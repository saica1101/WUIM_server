import json
import os
from config import OUTPUT_DIR, OUTPUT_FILE_PATH

def load_existing_data():
    """
    既存のJSONデータをロードする。
    ファイルが存在しない、または空の場合は空のリストを返す。
    Returns:
        list: ロードされたデータ（辞書のリスト）。
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True) # 出力ディレクトリが存在しない場合は作成
    if os.path.exists(OUTPUT_FILE_PATH) and os.path.getsize(OUTPUT_FILE_PATH) > 0:
        try:
            with open(OUTPUT_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Existing JSON file '{OUTPUT_FILE_PATH}' is empty or corrupted. Starting fresh.")
            return []
    return []

def save_data(data):
    """
    データをJSONファイルに保存する。
    Args:
        data (list): 保存するデータ（辞書のリスト）。
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True) # 念のため再度ディレクトリ作成
    with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)