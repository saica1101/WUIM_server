import time
import os
import json
import datetime
import config
import scraper
import nlp_analyzer # ★nlp_analyzer をインポート

def main():
    print("[{}] Starting Windows Latest issue scraper...".format(datetime.datetime.now()))

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
    relevant_articles = scraper.filter_relevant_articles(article_links)
    print("[{}] Filtered down to {} relevant articles based on keywords and URL structure.".format(datetime.datetime.now(), len(relevant_articles)))

    processed_articles_data = []

    # 4. 各記事の詳細ページから本文を抽出
    for i, article in enumerate(relevant_articles):
        current_time = datetime.datetime.now()
        print("[{}] Processing article {}/{}: {} ({})".format(current_time, i+1, len(relevant_articles), article['title'], article['url']))

        # 既に処理済みかチェック
        # (ここでは既存のJSONからロードするロジックは省略。必要であれば追加)

        article_content = scraper.extract_article_content(article['url'])

        if article_content:
            # デバッグ用プリント
            print(f"DEBUG: Article Title before append: {article['title']}")
            print(f"DEBUG: Article URL before append: {article['url']}")

            article_data = {
                "timestamp": current_time.isoformat(),
                "article_title": article['title'], # ここに値が正しく入っているか？
                "article_url": article['url'],     # ここに値が正しく入っているか？
                "content": article_content
            }
            processed_articles_data.append(article_data)
        else:
            print("[{}] Could not extract content for: {}".format(current_time, article['title']))
        
        scraper.apply_random_delay() # サーバー負荷軽減のための遅延

    # 5. NLPアナライザーで記事を処理し、JSONに出力
    if processed_articles_data:
        print(f"[{datetime.datetime.now()}] Analyzing {len(processed_articles_data)} articles with NLP...")
        nlp_analyzer.process_and_save_issue_data_nlp(processed_articles_data)
    else:
        print(f"[{datetime.datetime.now()}] No articles to analyze after content extraction.")

    print("[{}] Scraper finished.".format(datetime.datetime.now()))

if __name__ == "__main__":
    main()