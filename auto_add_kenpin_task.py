#!/usr/bin/env python3
"""
献品データ入力タスク自動追加スクリプト

毎月月末（その月の最終日）に実行し、「献品データ入力」タスクを
日常業務プロジェクトに自動追加します。
"""

import os
import calendar
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# Notion設定
NOTION_TOKEN = os.getenv("NOTION_TOKEN_TASK")
TASK_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"  # 祖霊社タスクDB
DAILY_PROJECT_ID = "1c900160-1818-80da-9ba3-d5fda958514f"  # 日常業務プロジェクト

# タスク名
TASK_NAME = "献品データ入力"

def log(message: str):
    """ログ出力"""
    timestamp = datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def is_last_day_of_month(dt: datetime) -> bool:
    """今日がその月の最終日かどうかをチェック"""
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return dt.day == last_day


def check_existing_task(task_name: str) -> bool:
    """同名の未完了タスクが既に存在するかチェック"""
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }

    data = {
        "filter": {
            "and": [
                {"property": "プロジェクト名", "relation": {"contains": DAILY_PROJECT_ID}},
                {"property": "タスク名", "title": {"equals": task_name}},
                {"property": "進捗", "status": {"does_not_equal": "完了"}}
            ]
        }
    }

    response = requests.post(
        f'https://api.notion.com/v1/databases/{TASK_DB_ID}/query',
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        results = response.json().get('results', [])
        return len(results) > 0
    return False


def add_task(task_name: str, deadline: str) -> bool:
    """タスクを追加"""
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }

    payload = {
        "parent": {"database_id": TASK_DB_ID},
        "properties": {
            "タスク名": {
                "title": [{"type": "text", "text": {"content": task_name}}]
            },
            "プロジェクト名": {
                "relation": [{"id": DAILY_PROJECT_ID}]
            },
            "タグ": {
                "multi_select": [{"name": "日常業務"}]
            },
            "期限": {
                "date": {"start": deadline}
            },
            "進捗": {
                "status": {"name": "未了"}
            }
        }
    }

    response = requests.post(
        'https://api.notion.com/v1/pages',
        headers=headers,
        json=payload
    )

    if response.status_code >= 400:
        log(f"エラー: {response.status_code} - {response.json().get('message', '')}")
        return False
    return True


def main():
    """メイン処理"""
    print("=" * 60)
    print("献品タスク自動追加スクリプト")
    print("=" * 60)

    if not NOTION_TOKEN:
        log("エラー: NOTION_TOKEN_TASKが設定されていません")
        return

    # 日本時間で今日の日付を取得
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    deadline = now.strftime('%Y-%m-%d')

    log(f"本日 ({deadline}) を期限として献品タスクを追加中...")

    # 重複チェック
    if check_existing_task(TASK_NAME):
        log(f"スキップ: 「{TASK_NAME}」は既に未完了タスクとして存在します")
        print("=" * 60)
        print("完了: タスクは既に存在するため追加しませんでした")
        print("=" * 60)
        return

    # タスク追加
    if add_task(TASK_NAME, deadline):
        log(f"追加: {TASK_NAME}")
        print("=" * 60)
        print("完了: 1件のタスクを追加しました")
        print("=" * 60)
    else:
        log(f"失敗: {TASK_NAME}")
        print("=" * 60)
        print("エラー: タスクの追加に失敗しました")
        print("=" * 60)


if __name__ == "__main__":
    main()
