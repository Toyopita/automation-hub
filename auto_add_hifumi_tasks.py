#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ひふみタスク自動追加スクリプト

毎月月末にひふみプロジェクトの定例タスク10件をNotionに自動追加する。
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# .envファイルから環境変数を読み込む
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# 環境変数から取得
NOTION_TOKEN = os.environ.get('NOTION_TOKEN_TASK')
HIFUMI_PROJECT_ID = "2ad00160-1818-815f-8359-f04889f4d9d2"
TASK_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"
USER_ID = "4463c065-1795-49cf-a939-1b018b08e25b"  # Minami

# 追加するタスクリスト
TASKS = [
    "1面構成作成",
    "2面構成作成",
    "原稿依頼",
    "紙面レイアウト作成",
    "データ提出",
    "構成最終確認",
    "分祠長確認",
    "1面の教主御教え選出",
    "ひふみ1面掲載記事確定",
    "ひふみ修正",
    "1面の写真確定"
]


def check_existing_task_by_name(task_name):
    """タスク名でひふみプロジェクトのタスクが既に存在するかチェック（未完了のみ）"""
    try:
        url = "https://api.notion.com/v1/databases/{}/query".format(TASK_DB_ID)
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        data = {
            "filter": {
                "and": [
                    {
                        "property": "プロジェクト名",
                        "relation": {"contains": HIFUMI_PROJECT_ID}
                    },
                    {
                        "property": "タスク名",
                        "title": {"equals": task_name}
                    },
                    {
                        "property": "進捗",
                        "status": {"does_not_equal": "完了"}
                    }
                ]
            }
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            results = response.json().get('results', [])
            return len(results) > 0
        else:
            print(f"警告: タスク検索失敗: {response.text}")
            return False

    except Exception as e:
        print(f"警告: タスク検索エラー: {e}")
        return False


def add_task_to_notion(task_name, deadline):
    """Notionにタスクを追加"""
    try:
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        data = {
            "parent": {"database_id": TASK_DB_ID},
            "properties": {
                "タスク名": {"title": [{"text": {"content": task_name}}]},
                "プロジェクト名": {"relation": [{"id": HIFUMI_PROJECT_ID}]},
                "期限": {"date": {"start": deadline}},
                "タグ": {"multi_select": [{"name": "ひふみ"}]},
                "担当者": {"people": [{"id": USER_ID}]}
            }
        }

        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200

    except Exception as e:
        print(f"  エラー: {task_name} の追加中にエラー: {e}")
        return False


def get_last_day_of_month():
    """今月の最終日を取得"""
    now = datetime.now(ZoneInfo('Asia/Tokyo'))
    # 翌月の1日から1日引いて今月の最終日を取得
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, tzinfo=ZoneInfo('Asia/Tokyo'))
    else:
        next_month = datetime(now.year, now.month + 1, 1, tzinfo=ZoneInfo('Asia/Tokyo'))
    last_day = next_month - timedelta(days=1)
    return last_day.strftime('%Y-%m-%d')


def add_monthly_tasks():
    """今月末の期限としてタスクを追加（タスクごとに重複チェック）"""
    from datetime import timedelta

    # 日本時間で今月末の日付を期限とする
    deadline = get_last_day_of_month()

    print(f"→ 今月末 ({deadline}) を期限としてひふみタスクを追加中...")

    added_count = 0
    skipped_count = 0

    for task_name in TASKS:
        # タスク名で未完了タスクが既に存在するかチェック
        if check_existing_task_by_name(task_name):
            print(f"  - スキップ: {task_name}（未完了タスクが既に存在）")
            skipped_count += 1
            continue

        if add_task_to_notion(task_name, deadline):
            print(f"  + 追加: {task_name}")
            added_count += 1

    print(f"  ✓ 追加: {added_count}件, スキップ: {skipped_count}件")
    return added_count


def main():
    print("=" * 60)
    print("ひふみタスク自動追加スクリプト")
    print("=" * 60)

    # Notionトークンチェック
    if not NOTION_TOKEN:
        print("エラー: NOTION_TOKEN_TASK が設定されていません")
        sys.exit(1)

    # タスク追加
    print("\n[1] ひふみタスクを追加中...")
    total_added = add_monthly_tasks()

    # 結果通知
    print("\n" + "=" * 60)
    print(f"完了: {total_added}件のタスクを追加しました")
    print("=" * 60)

    # macOS通知
    if total_added > 0:
        import subprocess
        subprocess.run([
            'osascript', '-e',
            f'display notification "ひふみタスク{total_added}件をNotionに追加しました" with title "ひふみタスク自動追加"'
        ])


if __name__ == '__main__':
    main()
