import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import urljoin, urlparse, urlunparse
import datetime # datetime をインポート

import config # config モジュール全体をインポート

def get_html_content(url):
    """
    指定されたURLからHTMLコンテンツを取得する。
    Args:
        url (str): 取得するURL。
    Returns:
        str: 取得したHTMLコンテンツ、またはエラーの場合はNone。
    """
    try:
        response = requests.get(url, headers=config.HEADERS, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_article_links(html_content):
    """
    HTMLコンテンツから記事のリンクとタイトルを抽出する。
    Args:
        html_content (str): HTML文字列。
    Returns:
        list: 記事情報 (title, url) の辞書リスト。
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []

    for selector in config.MAIN_PAGE_ARTICLE_LINK_SELECTORS:
        tag_name = selector.get('tag')
        class_name = selector.get('class_name')
        css_selector = selector.get('selector')

        # CSSセレクタが指定されていればそれを使用
        if css_selector:
            found_elements = soup.select(css_selector)
        elif tag_name and class_name:
            found_elements = soup.find_all(tag_name, class_=class_name)
        else:
            continue # 有効なセレクタ情報がない場合はスキップ

        for element in found_elements:
            href = element.get('href')
            title = element.get_text(strip=True) # タイトルを取得

            if href and title:
                links.append({'title': title, 'url': href})
    return links

def extract_article_content(article_url):
    """
    記事の詳細ページから本文コンテンツを抽出する。
    Args:
        article_url (str): 記事のURL。
    Returns:
        str: 抽出した記事本文、またはエラーの場合はNone。
    """
    html_content = get_html_content(article_url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    for selector in config.ARTICLE_CONTENT_SELECTORS:
        tag_name = selector.get('tag')
        class_name = selector.get('class_name')
        css_selector = selector.get('selector')

        content_div = None
        if css_selector:
            content_div = soup.select_one(css_selector)
        elif tag_name and class_name:
            content_div = soup.find(tag_name, class_=class_name)
        
        if content_div:
            # スクリプト、スタイル、広告などの不要な要素を削除
            for unwanted_tag in content_div.find_all(['script', 'style', 'ins', 'iframe', 'noscript', 'form']):
                unwanted_tag.decompose()
            
            # リンクのテキストだけ抽出したい場合は'a'タグをunwrapsする
            # for a_tag in content_div.find_all('a'):
            #     a_tag.unwrap() # aタグ自体を削除し、中のテキストを昇格させる

            return content_div.get_text(separator='\n', strip=True)

    print(f"Could not find article content for {article_url} with specified selectors.")
    return None

def filter_relevant_articles(article_links, last_check_time=None):
    """
    記事リンクをフィルタリングし、関連性の高いもの、かつ
    last_check_time以降に公開された可能性のあるもののみを抽出する。
    Args:
        article_links (list): 記事情報 (title, url) の辞書リスト。
        last_check_time (datetime.datetime): 前回の最終チェック時刻。
                                              これ以降に更新された記事のみを対象とする。
    Returns:
        list: フィルタリングされた記事情報 (title, url) の辞書リスト。
    """
    relevant_articles = []
    seen_urls = set()

    for article in article_links:
        title = article['title'].lower()
        url = article['url']

        # URLからフラグメント（#commentsなど）を削除
        parsed_url = urlparse(url)
        clean_url = urlunparse(parsed_url._replace(fragment=''))
        
        # Windows Latestのドメインに限定
        if config.WINDOWS_LATEST_URL not in clean_url:
            continue
        
        # 相対URLを完全なURLに変換
        if not clean_url.startswith('http'):
            clean_url = urljoin(config.WINDOWS_LATEST_URL, clean_url)

        # 重複するURLをスキップ（フラグメント除去後で判断）
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url) # 処理済みURLとしてマーク

        # "Read more" や "0" などの意味のないタイトルをフィルタリング
        if title.strip() in ["read more", "comments", "support document"] or title.strip().isdigit():
            continue

        # キーワードによる初期フィルタリング（不具合に関連しそうなもののみを対象とする）
        # URLにもキーワードが含まれるかチェック
        if not any(keyword in title or keyword in clean_url for keyword in config.ARTICLE_FILTER_KEYWORDS):
            continue
        
        # 日付によるフィルタリング (実装が難しい場合、URLやタイトルから推測するか、常に最新を取得)
        # Windows LatestのURL構造には日付情報が含まれないことが多いため、
        # ここで正確な日付フィルタリングは行わず、全ての関連記事をチェック対象とする。
        # 代わりに、main.pyでキャッシュと最終チェック時刻に基づいて処理をスキップする。
        # ただし、タイトルに年や月が含まれる場合は将来的に利用できるかもしれない。
        
        # もしlast_check_timeが指定されていて、記事の公開日時がそれより古い場合はスキップしたいが、
        # 現在のスクレイピング方法では記事の公開日時を効率的に取得できないため、
        # ここではあくまで「URLとタイトルからのフィルタリング」に留める。
        # キャッシュ機能側で、既に処理済みのURLであればスキップする仕組みに依存する。
        # もし特定の記事の公開日時が取得可能であれば、ここにロジックを追加できる。
        
        relevant_articles.append({'title': article['title'], 'url': clean_url})
    
    return relevant_articles

def apply_random_delay():
    """
    スクレイピング間のランダムな遅延を適用し、サーバーへの負荷を軽減する。
    """
    delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
    time.sleep(delay)