import re
import os

# 基本設定
WINDOWS_LATEST_URL = "https://www.windowslatest.com/"
OUTPUT_DIR = "output"
OUTPUT_FILE_NAME = "windows_update_issues.json"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILE_NAME)

# スクレイピング設定
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/533.36"
}
REQUEST_TIMEOUT = 10 # seconds

# 記事の関連性フィルタリング用キーワード(小文字で定義)
ARTICLE_FILTER_KEYWORDS = ["windows update", "update", "kb", "patch", "microsoft"]

# ネガティブな文言を判定するためのキーワード(小文字で定義)
# より広範囲な不具合を示す言葉を含める
NEGATIVE_KEYWORDS = [
    "failed", "error", "crash", "issue", "bug", "not working", "stuck",
    "freeze", "blue screen", "installation failed", "update issues",
    "problems", "broken", "vulnerability", "breaking", "malfunction",
    "corrupt", "unstable", "slow", "disabled", "cannot", "fix failed",
    "missing", "hang", "restart", "reboot loop", "incompatible", "conflict",
    "performance degradation", "data loss", "security flaw", "exploit", "bsod"
]

# 重要度：大を判定するためのキーワード(小文字で定義)
HIGH_SEVERITY_KEYWORDS = [
    "boot loop", "unbootable", "data loss", "system crash", "critical issue",
    "complete failure", "dead screen", "briked", "black screen", "major vulnerability",
    "reboot loop"
]

# KB番号を抽出するための正規表現パターン
# 例:KB1234567 KB 1234567, (KB1234567), KB-1234567, KB12345678
KB_PATTERN = re.compile(r"KB\s?(\d{7,8})", re.IGNORECASE)

# Windows LatestのHTML要素セレクタ
# main_page_article_link_selectors: メインページから記事リンクを抽出するためのCSSセレクタのリスト
#    - h2.entry-title a: メインブログ記事のタイトルリンク
#    - a.category-box-link h3: カテゴリボックス内の記事リンク
MAIN_PAGE_ARTICLE_LINK_SELECTORS = [
    # h2タグの中にあるrel="bookmark"を持つaタグ
    {'tag': 'h2', 'class_': 'entry-title', 'find_a': True, 'attrs': {'rel': 'bookmark'}},
    # h3タグの中にあるrel="bookmark"を持つaタグ (もしh3も使われているなら)
    {'tag': 'h3', 'class_': 'entry-title', 'find_a': True, 'attrs': {'rel': 'bookmark'}},
    # トップページにある「Latest Posts」のようなセクションで、直接rel="bookmark"を持つaタグがある場合
    {'tag': 'a', 'attrs': {'rel': 'bookmark'}}
]

# NLP 関連の設定
# ポジティブな感情を示すキーワード（不具合ではないことを示唆）
NLP_POSITIVE_KEYWORDS = [
    "fixed", "solved", "resolved", "improved", "new feature", "release", "update available",
    "enhancement", "patch", "out now", "optimizations", "better", "security update",
    "windows 10","windows server" # Windows 11のみに絞る
]

# ネガティブな感情を示すキーワード（不具合である可能性を示唆）
NLP_NEGATIVE_KEYWORDS = [
    "bug", "error", "issue", "crash", "freeze", "fail", "stuck", "problem",
    "vulnerability", "exploit", "slow", "hang", "security flaw", "data loss",
    "broken", "malware", "ransomware", "unstable", "performance drop", "not working",
    "blue screen", "bsod", "installation failed", "update issues", "problems",
    "corrupt", "incompatible", "conflict", "missing", "restart", "reboot loop",
    "uninstall", # アンインストールが必要な場合も問題の可能性
    "cannot", "failed to", "unable to", # 汎用的な失敗を示すフレーズ
    "kb5", # KB番号のパターンの一部を追加 (KB5063060 など)
    "fails", "failure"
]

# 重大度を上げるキーワード
NLP_HIGH_SEVERITY_KEYWORDS = [
    "critical", "major", "severe", "serious", "data loss", "unbootable",
    "system crash", "permanent damage", "zero-day", "exploit", "ransomware",
    "kernel panic", "bricked", "loop", "security vulnerability", "install fails", # 追加
    "update fails", "boot issue", "corrupted"
]

# 軽度な感情を示すキーワード（不具合ではない可能性が高い）
NLP_LOW_SEVERITY_KEYWORDS = [
    "minor", "small", "cosmetic", "visual glitch", "annoyance"
]

# article_content_selector: 記事詳細ページから本文を抽出するためのセレクタ
ARTICLE_CONTENT_SELECTOR = {'tag': 'div', 'class_': 'td-post-content tagdiv-type'}