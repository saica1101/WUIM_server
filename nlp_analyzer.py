import spacy
from textblob import TextBlob
import re
import json
import os
import config # config.pyをインポート
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI API KEYが設定されていません")
    exit()

if GEMINI_API_KEY:
    genai.configure(api_key = GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
else:
    model = None

# spaCyモデルのロード (初回実行時にダウンロードが必要: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run: python -m spacy download en_core_web_sm")
    exit()

def analyze_sentiment_and_keywords(text):
    """
    TextBlobを使用してテキストの感情分析を行い、spaCyでキーワードとエンティティを抽出する。
    Args:
        text (str): 分析対象のテキスト。
    Returns:
        dict: 感情スコア、主要キーワード、検出されたエンティティを含む辞書。
    """
    # TextBlobによる感情分析
    blob = TextBlob(text)
    sentiment_polarity = blob.sentiment.polarity # -1.0 (ネガティブ) から 1.0 (ポジティブ)
    sentiment_subjectivity = blob.sentiment.subjectivity # 0.0 (客観的) から 1.0 (主観的)

    # spaCyによるキーワード (名詞句) とエンティティ抽出
    doc = nlp(text)
    
    # 名詞句をキーワードとして抽出（重複排除）
    keywords = list(set([chunk.text.lower() for chunk in doc.noun_chunks if not chunk.text.lower().isnumeric()]))

    # 固有表現 (NER) 抽出
    entities = list(set([ent.text.lower() for ent in doc.ents]))

    return {
        "sentiment_polarity": sentiment_polarity,
        "sentiment_subjectivity": sentiment_subjectivity,
        "keywords": keywords,
        "entities": entities
    }

def extract_kb_numbers(text):
    """
    テキストからKB番号（KBXXXXXXXX形式）を抽出する。
    Args:
        text (str): 抽出対象のテキスト。
    Returns:
        list: 検出されたKB番号のリスト。
    """
    # KBに続く7桁以上の数字を検出する正規表現（大文字小文字を区別しない）
    kb_pattern = re.compile(r'KB(\d{7,})', re.IGNORECASE)
    return list(set(kb_pattern.findall(text))) # 重複排除

def assess_issue_severity_nlp(title, content):
    """
    記事のタイトルと本文に基づいて不具合の重大度をNLPで判定する。
    Args:
        title (str): 記事のタイトル。
        content (str): 記事の本文。
    Returns:
        tuple: (severity, detected_keywords, kb_numbers, sentiment_polarity)
    """
    text_to_analyze = (title + " " + content).lower()
    severity = "low"
    detected_keywords = []
    
    kb_numbers = extract_kb_numbers(text_to_analyze) # KB番号を抽出

    # 高重大度キーワードの検出
    high_severity_found = False
    for keyword in config.NLP_HIGH_SEVERITY_KEYWORDS:
        if keyword in text_to_analyze:
            severity = "high"
            detected_keywords.append(keyword)
            high_severity_found = True
            break # 最も高い重要度が見つかったら終了

    # ネガティブキーワードの検出（high_severity_found が True でなければ実行）
    if not high_severity_found:
        for keyword in config.NLP_NEGATIVE_KEYWORDS:
            if keyword in text_to_analyze:
                detected_keywords.append(keyword)
                if severity == "low": # lowからmediumに昇格
                    severity = "medium"
    
    # ここで、検出されたキーワードからポジティブキーワードを削除する
    final_detected_keywords = []
    for keyword in detected_keywords:
        is_positive_context = False
        for pos_kw in config.NLP_POSITIVE_KEYWORDS:
            # ポジティブキーワードがネガティブキーワードの近くにあるか簡易的にチェック
            # 例: "fixed bug" のように、"bug" の近くに "fixed" がある場合
            if pos_kw in text_to_analyze and \
               abs(text_to_analyze.find(pos_kw) - text_to_analyze.find(keyword)) < 20: # 20文字以内
                is_positive_context = True
                break
        if not is_positive_context:
            final_detected_keywords.append(keyword)
    
    # KB番号が検出された場合、最低でもmediumにする
    if kb_numbers and severity == "low":
        severity = "medium"
        # KB番号を検出キーワードとして追加する（オプション）
        # final_detected_keywords.extend([f"KB:{kb}" for kb in kb_numbers])

    # TextBlobによる感情分析
    blob = TextBlob(text_to_analyze)
    sentiment_polarity = blob.sentiment.polarity

    # 重複を排除して最終的な検出キーワードリストを作成
    final_detected_keywords = list(set(final_detected_keywords))

    return severity, final_detected_keywords, kb_numbers, sentiment_polarity

def ask_gemini_about_severity(article_title, article_content, kb_numbers, detected_keywords):
    """
    Gemini APIを利用して、記事が「Windowsの重大な不具合」に関するものか判定する
    Args:
        article_title (str): 記事のタイトル
        article_content (str): 記事の本文
        kb_numbers (list): 検出されたKB番号のリスト
        detected_keywords (list): 検出されたキーワードのリスト
    Returns:
        str: 重大な不具合に関するものならTrue, そうでなければFalse
    """
    if not model:
        return False
    prompt = f"""
    以下の記事は、Windowsの重大な不具合、またはその修正に関する情報ですか？
    「重大な不具合」とは、OSの機能停止、データ損失、セキュリティ脆弱性、パフォーマンスの著しい低下、特定の重要な機能が利用不可になるなどの、ユーザー体験に大きな悪影響を及ぼす問題を指します。
    単なる機能紹介、ヒント、古いニュース、製品の比較、リリース情報(不具合の言及がない場合)、あるいは軽微な視覚的バグやUIの変更に関する記事は「重大な不具合」ではありません。
    また、「after」などの単語が含まれていた場合は、単なる「後の」情報であり、重大な不具合ではない可能性が高いので注意してください。(例：Windows 10 KB5063159 released after June patch trashes Surface Hub v1)
    さらに影響が及ぶ範囲をWindows 11 に限定します。タイトル中にWindows 10 や Windows Server などの指定がある場合、重大な不具合ではないと判断してください。

    この記事にはKB番号: {', '.join(kb_numbers) if kb_numbers else 'なし'} が含まれ、
    関連キーワードとして: {', '.join(detected_keywords) if detected_keywords else 'なし'} が検出されています。

    記事のタイトル: "{article_title}"
    記事の本文の冒頭: "{article_content[:500]}..."

    この記事は「重大な不具合に関するもの」である場合のみ「はい」と答えてください。それ以外の場合は「いいえ」と答えてください。
    回答は「はい」または「いいえ」のみにしてください。
    """
    try:
        response = model.generate_content(prompt)
        # 応答がTextオブジェクトの場合、text属性から文字列を取得
        response_text = response.text.strip().lower()
        print(f"Gemini判定結果: {response_text} (記事: {article_title[:50]}...)")
        return response_text == "はい"
    
    except Exception as e:
        print(f"Gemini API呼び出しエラー: {e}")
        # APIエラー時はGeminiによる判定をスキップし、Falseを返すなどのフォールバックを検討
        return False

def process_and_save_issue_data_nlp(articles):
    """
    収集した記事データをNLPで分析し、不具合情報をJSONファイルに保存する。
    Args:
        articles (list): 記事情報 (title, url, content) の辞書リスト。
    """
    output_data = []
    issues_found = 0

    for article in articles:
        article_title = article.get('article_title', '')
        article_url = article.get('article_url', '')
        article_content = article.get('content', '')

        if not article_content:
            print(f"Skipping article due to empty content: {article_title}")
            continue

        # 1. 簡易NLPによる重大度判定（KB検出を含む）
        severity, detected_keywords, kb_numbers, sentiment_polarity = \
            assess_issue_severity_nlp(article_title, article_content)

        # 2. KB番号が検出されなかった場合、またはNLPが"low"と判定した場合は、ここでスキップ
        # GeminiにAPIコールする前に、ある程度絞り込む
        if not kb_numbers and severity == "low":
            # KB番号がなく、かつNLPが既に「low」と判断した場合は、Geminiに聞かずにスキップ
            continue
        
        # 3. Geminiによる最終判別（KB番号があるか、またはNLPでmedium/highと判定された記事のみ）
        is_truly_critical_issue = False
        if model: # Geminiモデルが利用可能な場合のみAPIコール
            is_truly_critical_issue = ask_gemini_about_severity(
                article_title, article_content, kb_numbers, detected_keywords
            )
        else:
            # Geminiが利用できない場合、NLPのseverityに頼る
            # ここでは、KBがあるか、NLPがmedium/highと判断したら含めるようにする
            is_truly_critical_issue = (len(kb_numbers) > 0 or severity in ["high", "medium"])

        # Geminiが「はい」と判断した場合、またはGeminiが利用できずNLPで十分と判断した場合に含める
        if is_truly_critical_issue:
            output_entry = {
                "timestamp": article.get('timestamp', ''),
                "article_title": article_title,
                "article_url": article_url,
                "kb_numbers": kb_numbers,
                # Geminiで最終的に「重大な不具合」と判断されたので、severityは"high"とする
                # もしGeminiがより細かいseverityを返せるなら、それを利用
                "severity": "high", 
                "detected_keywords": detected_keywords,
                "sentiment_polarity": sentiment_polarity,
                "content_preview": article_content[:200] + "..." if len(article_content) > 200 else article_content
            }
            output_data.append(output_entry)
            issues_found += 1

    # outputディレクトリが存在しない場合は作成
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file_path = os.path.join(output_dir, "windows_update_issues_gemini.json") # ファイル名を変更

    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    print(f"Found {issues_found} relevant issues using Gemini. Data saved to {output_file_path}")