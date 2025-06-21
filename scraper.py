import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import urljoin, urlparse, urlunparse # urlparse, urlunparse を追加

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
        response = requests.get(url, headers=config.HEADERS, timeout=config.REQUEST_TIMEOUT) # config.HEADERS, config.REQUEST_TIMEOUT
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

    for selector in config.MAIN_PAGE_ARTICLE_LINK_SELECTORS: # config.MAIN_PAGE_ARTICLE_LINK_SELECTORS
        tag_name = selector.get('tag')
        class_name = selector.get('class_')
        find_a = selector.get('find_a')
        attrs = selector.get('attrs', {})

        search_args = {}
        if tag_name:
            search_args['name'] = tag_name
        if class_name:
            search_args['class_'] = class_name
        if attrs:
            search_args['attrs'] = attrs

        if find_a:
            found_parents = soup.find_all(**search_args)
            for parent_tag in found_parents:
                a_tag = parent_tag.find('a', href=True, **selector.get('attrs', {})) # rel="bookmark"などの属性をaタグ検索に渡す
                if a_tag and a_tag.get('href'):
                    links.append({
                        'title': a_tag.get_text(strip=True),
                        'url': a_tag['href']
                    })
        else:
            found_a_tags = soup.find_all(**search_args)
            for a_tag in found_a_tags:
                if a_tag.name == 'a' and a_tag.get('href'):
                    links.append({
                        'title': a_tag.get_text(strip=True),
                        'url': a_tag['href']
                    })
    
    unique_links = {link['url']: link for link in links}.values()
    return list(unique_links)

def extract_article_content(article_url):
    """
    記事のURLから本文コンテンツを抽出する。
    Args:
        article_url (str): 記事のURL。
    Returns:
        str: 抽出された記事の本文テキスト、またはエラーの場合はNone。
    """
    html_content = get_html_content(article_url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    content_tag = soup.find(config.ARTICLE_CONTENT_SELECTOR['tag'], class_=config.ARTICLE_CONTENT_SELECTOR.get('class_')) # config.ARTICLE_CONTENT_SELECTOR
    
    if content_tag:
        # 不要な要素を削除
        for nav_tag in content_tag.find_all('nav', class_='post-content-nav'):
            nav_tag.extract()
        for form_tag in content_tag.find_all('form', class_=re.compile(r'fluentform')):
            form_tag.extract()
        for social_share_div in content_tag.find_all('div', class_='wlsocial share'):
            social_share_div.extract()
        for youtube_embed_div in content_tag.find_all('div', class_='youtube-embed'):
            youtube_embed_div.extract()
        for figcaption_tag in content_tag.find_all('figcaption'):
            figcaption_tag.extract()
        for image_div in content_tag.find_all('div', class_='td-post-featured-image'): # 画像の親divも削除
            image_div.extract()

        paragraphs = content_tag.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        article_text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        return article_text
    return None

def filter_relevant_articles(article_links):
    """
    キーワードとURLに基づいて関連性の低い記事をフィルタリングする。
    Args:
        article_links (list): 記事情報 (title, url) の辞書リスト。
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
        if config.WINDOWS_LATEST_URL not in clean_url: # config.WINDOWS_LATEST_URLを使用
            continue
        
        # 相対URLを完全なURLに変換
        if not clean_url.startswith('http'):
            clean_url = urljoin(config.WINDOWS_LATEST_URL, clean_url) # config.WINDOWS_LATEST_URLを使用

        # 重複するURLをスキップ（フラグメント除去後で判断）
        if clean_url in seen_urls:
            continue
        
        # "Read more" や "0" などの意味のないタイトルをフィルタリング
        if title.strip() == "read more" or title.strip().isdigit() or title.strip() == "comments" or title.strip() == "support document":
            continue

        # キーワードによる初期フィルタリング（不具合に関連しそうなもののみを対象とする）
        if any(keyword in title or keyword in clean_url for keyword in config.ARTICLE_FILTER_KEYWORDS):
            article['url'] = clean_url
            relevant_articles.append(article)
            seen_urls.add(clean_url)
            
    return relevant_articles

def apply_random_delay(min_sec=1, max_sec=3):
    """リクエスト間にランダムな遅延を入れる"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)