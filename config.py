import os
import re
# import appdirs # appdirs は不要になるため削除

# ==============================================================================
# 基本設定
# ==============================================================================
WINDOWS_LATEST_URL = "https://www.windowslatest.com/"

# アプリケーションデータを保存するディレクトリの決定
# プログラム実行ディレクトリ直下に 'output' ディレクトリを作成し、その中に全てを保存する
# (.\WUIM_server\output\...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # config.pyが存在するディレクトリ
OUTPUT_DIR = os.path.join(BASE_DIR, "output") # outputフォルダを .\WUIM_server\output に設定

# 出力ファイル設定
OUTPUT_FILE_NAME = "windows_update_issues_gemini.json"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILE_NAME)

# キャッシュファイル設定
# キャッシュディレクトリも output フォルダ内に作成 (.\WUIM_server\output\cache)
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
CACHED_REMOTE_JSON_FILE_NAME = "cached_remote_issues.json"
CACHED_REMOTE_JSON_FILE_PATH = os.path.join(CACHE_DIR, CACHED_REMOTE_JSON_FILE_NAME)

# 最終チェック時刻ファイル設定 (キャッシュディレクトリ内に保存)
LAST_CHECK_FILE_NAME = "last_check_time.txt"
LAST_CHECK_FILE_PATH = os.path.join(CACHE_DIR, LAST_CHECK_FILE_NAME)

# ==============================================================================
# スクレイピング設定
# ==============================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/533.36"
}
REQUEST_TIMEOUT = 10 # seconds

# メインページからの記事リンク抽出用セレクタ (リスト形式で複数の候補を指定可能)
# 優先順位が高いものから順に記載
MAIN_PAGE_ARTICLE_LINK_SELECTORS = [
    {'tag': 'h2', 'class_name': 'entry-title', 'selector': 'h2.entry-title a'},
    {'tag': 'h3', 'class_name': 'entry-title', 'selector': 'h3.entry-title a'},
    {'tag': 'a', 'class_name': 'post-title-link', 'selector': 'a.post-title-link'}, # 例として追加
    # 他にも候補があればここに追加
]

# 記事本文の抽出用セレクタ (最も具体的なものを優先)
ARTICLE_CONTENT_SELECTORS = [
    {'tag': 'div', 'class_name': 'entry-content', 'selector': 'div.entry-content'},
    {'tag': 'div', 'class_name': 'td-post-content', 'selector': 'div.td-post-content'}, # 例として追加
    # 他にも候補があればここに追加
]

# ==============================================================================
# 記事の関連性フィルタリング用キーワード (小文字で定義)
# ==============================================================================
ARTICLE_FILTER_KEYWORDS = ["windows update", "update", "kb", "patch", "microsoft", "build"]

# ==============================================================================
# NLP/Gemini 分析用キーワード
# ==============================================================================

# ポジティブな感情を示すキーワード（不具合ではない可能性を示唆）
NLP_POSITIVE_KEYWORDS = [
    "fixed", "solved", "resolved", "improved", "new feature", "release", "update available",
    "enhancement", "patch", "out now", "optimizations", "better", "security update",
    "windows 10", "windows server" # Gemini promptでWindows 11 に限定する指示があるため、これらが記事タイトルや本文にある場合は除外対象としたい
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
    "fails", "failure", "after" # "after" が含まれる場合もGemini promptでネガティブになるよう指示
]

# 重大度を上げるキーワード
NLP_HIGH_SEVERITY_KEYWORDS = [
    "critical", "major", "severe", "serious", "data loss", "unbootable",
    "system crash", "permanent damage", "zero-day", "exploit", "ransomware"
]

# KB番号抽出のための正規表現 (大文字小文字を区別しない)
KB_NUMBER_PATTERN = re.compile(r'KB(\d{7,})', re.IGNORECASE)

# ==============================================================================
# 遅延設定 (サーバーへの負荷軽減のため)
# ==============================================================================
MIN_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 5