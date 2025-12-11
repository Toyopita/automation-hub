#!/usr/bin/env python3
"""
落ち葉掃除タスク自動追加スクリプト

11月1日〜12月15日の偶数日に実行し、「落ち葉掃除」タスクを
日常業務プロジェクトに自動追加します。
"""

import os
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
TASK_NAME = "落ち葉掃除"


def log(message: str):
    """ログ出力"""
    timestamp = datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def is_ochiba_season(dt: datetime) -> bool:
    """落ち葉シーズン（11/1〜12/15）かどうかをチェック"""
    month = dt.month
    day = dt.day

    # 11月は全日対象
    if month == 11:
        return True
    # 12月は1日〜15日が対象
    elif month == 12 and day <= 15:
        return True
    return False


def is_even_day(dt: datetime) -> bool:
    """偶数日かどうかをチェック"""
    return dt.day % 2 == 0


def check_existing_task(task_name: str, deadline: str) -> bool:
    """同日の同名タスクが既に存在するかチェック"""
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
                {"property": "期限", "date": {"equals": deadline}}
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
    print("落ち葉掃除タスク自動追加スクリプト")
    print("=" * 60)

    if not NOTION_TOKEN:
        log("エラー: NOTION_TOKEN_TASKが設定されていません")
        return

    # 日本時間で今日の日付を取得
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    deadline = now.strftime('%Y-%m-%d')

    log(f"本日: {deadline} ({now.month}月{now.day}日)")

    # 落ち葉シーズンチェック（11/1〜12/15）
    if not is_ochiba_season(now):
        log(f"スキップ: 落ち葉シーズン外です（対象: 11/1〜12/15）")
        print("=" * 60)
        print("完了: 落ち葉シーズン外のため実行をスキップしました")
        print("=" * 60)
        return

    # 偶数日チェック
    if not is_even_day(now):
        log(f"スキップ: 今日 ({now.day}日) は奇数日です（偶数日のみ実行）")
        print("=" * 60)
        print("完了: 奇数日のため実行をスキップしました")
        print("=" * 60)
        return

    log(f"本日 ({deadline}) は落ち葉シーズンの偶数日です。タスクを追加中...")

    # 重複チェック
    if check_existing_task(TASK_NAME, deadline):
        log(f"スキップ: 「{TASK_NAME}」は本日分が既に存在します")
        print("=" * 60)
        print("完了: タスクは既に存在するため追加しませんでした")
        print("=" * 60)
        return

    # タスク追加
    if add_task(TASK_NAME, deadline):
        log(f"追加: {TASK_NAME} (期限: {deadline})")
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
