import time
import os
import json
import datetime
import config
import scraper
import nlp_analyzer

def main():
    print("[{}] Starting Windows Latest issue scraper...".format(datetime.datetime.now()))

    # outputディレクトリとcacheディレクトリが存在しない場合は作成
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.CACHE_DIR, exist_ok=True)

    # 最終チェック時刻の読み込み
    last_check_time = None
    if os.path.exists(config.LAST_CHECK_FILE_PATH):
        try:
            with open(config.LAST_CHECK_FILE_PATH, 'r', encoding='utf-8') as f:
                last_check_time_str = f.read().strip()
                if last_check_time_str:
                    last_check_time = datetime.datetime.fromisoformat(last_check_time_str)
                    print(f"[{datetime.datetime.now()}] Last check time loaded: {last_check_time}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Error reading last check time file: {e}")
            last_check_time = None # エラー時はキャッシュを使わない

    # キャッシュされた記事データを読み込む
    cached_articles = {} # URLをキーとする
    if os.path.exists(config.CACHED_REMOTE_JSON_FILE_PATH):
        try:
            with open(config.CACHED_REMOTE_JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                cached_list = json.load(f)
                for entry in cached_list:
                    if 'article_url' in entry:
                        cached_articles[entry['article_url']] = entry
            print(f"[{datetime.datetime.now()}] Loaded {len(cached_articles)} articles from cache.")
        except json.JSONDecodeError:
            print(f"[{datetime.datetime.now()}] Warning: Cached JSON file {config.CACHED_REMOTE_JSON_FILE_PATH} is corrupt or empty. Starting with fresh cache.")
            cached_articles = {} # 無効なJSONの場合は空にする
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Error loading cached articles: {e}. Starting with fresh cache.")
            cached_articles = {}

    # 1. メインページのHTMLコンテンツを取得
    print("[{}] Fetching home page: {}".format(datetime.datetime.now(), config.WINDOWS_LATEST_URL))
    home_page_html = scraper.get_html_content(config.WINDOWS_LATEST_URL)

    if not home_page_html:
        print("[{}] Failed to fetch home page. Exiting.".format(datetime.datetime.now()))
        return

    # 2. 記事リンクを抽出
    article_links = scraper.extract_article_links(home_page_html)
    print("[{}] Found {} potential article links on homepage.".format(datetime.datetime.now(), len(article_links)))

    # 3. 関連性の高い記事をフィルタリング
    # ここでは、URLのクリーンアップも含むfilter_relevant_articlesを使用
    relevant_articles = scraper.filter_relevant_articles(article_links, last_check_time) # last_check_timeを渡す
    print("[{}] Filtered down to {} relevant articles (including new/updated since last check) based on keywords and URL structure.".format(datetime.datetime.now(), len(relevant_articles)))

    processed_articles_data = []
    
    # 処理済みの記事URLを追跡するセット
    urls_processed_in_this_run = set()

    # 4. 各記事の詳細ページから本文を抽出
    for i, article in enumerate(relevant_articles):
        current_time = datetime.datetime.now()
        article_url_cleaned = article['url'] # scraperでクリーンアップ済み
        
        # 既に今回処理済み、またはキャッシュにあり更新がない記事はスキップ
        if article_url_cleaned in urls_processed_in_this_run:
            print(f"[{current_time}] Skipping duplicate URL in current run: {article_url_cleaned}")
            continue

        # キャッシュに存在し、かつ今回の実行で更新がない場合はスキップ
        # (scraper.filter_relevant_articlesでlast_check_timeに基づいてフィルタリングしているため、
        # ここでは基本的には新規または更新された記事が来るはずですが、念のため)
        if article_url_cleaned in cached_articles:
            # ここではURLが既に存在することを確認するだけで、コンテンツのハッシュ比較などは行わない
            # scraperがタイムスタンプベースでフィルタリングしているので、基本的に不要
            pass
        
        print("[{}] Processing article {}/{}: {} ({})".format(current_time, i+1, len(relevant_articles), article['title'], article_url_cleaned))

        article_content = scraper.extract_article_content(article_url_cleaned) # クリーンアップされたURLを渡す

        if article_content:
            article_data = {
                "timestamp": current_time.isoformat(),
                "article_title": article['title'],
                "article_url": article_url_cleaned,
                "content": article_content
            }
            processed_articles_data.append(article_data)
            urls_processed_in_this_run.add(article_url_cleaned) # 処理済みとしてマーク
        else:
            print("[{}] Could not extract content for: {}".format(current_time, article['title']))
        
        scraper.apply_random_delay() # サーバー負荷軽減のための遅延

    # 新しく取得・更新した記事をキャッシュに追加/更新
    for article_data in processed_articles_data:
        cached_articles[article_data['article_url']] = article_data

    # キャッシュをファイルに保存
    if cached_articles:
        try:
            with open(config.CACHED_REMOTE_JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                # リスト形式で保存
                json.dump(list(cached_articles.values()), f, ensure_ascii=False, indent=4)
            print(f"[{datetime.datetime.now()}] Cached {len(cached_articles)} articles to {config.CACHED_REMOTE_JSON_FILE_PATH}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Error saving cached articles: {e}")

    # 5. NLPアナライザーで記事を処理し、JSONに出力
    # ここではcached_articlesのデータ（全てのスキャン対象記事）を渡す
    if cached_articles: # キャッシュされた記事が存在すれば分析を行う
        print(f"[{datetime.datetime.now()}] Analyzing {len(cached_articles)} articles with NLP...")
        # nlp_analyzerは既存のJSONを読み込み、新しいデータをマージするロジックを持つため、
        # ここでは cached_articles の内容を渡すのが適切
        nlp_analyzer.process_and_save_issue_data_nlp(list(cached_articles.values()))
    else:
        print(f"[{datetime.datetime.now()}] No articles to analyze.")


    # 最終チェック時刻を記録
    try:
        with open(config.LAST_CHECK_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(datetime.datetime.now().isoformat())
        print(f"[{datetime.datetime.now()}] Last check time updated to {datetime.datetime.now().isoformat()}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error writing last check time file: {e}")

    print("[{}] Scraper finished.".format(datetime.datetime.now()))

if __name__ == "__main__":
    main()