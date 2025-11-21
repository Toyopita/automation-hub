#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年次庭剪定タスク自動追加スクリプト

毎年5月1日に実行され、庭剪定タスク3件をNotionに自動追加する。
"""

import os
import sys
import requests
from datetime import datetime
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
TASK_DB_ID = '1c800160-1818-807c-b083-f475eb3a07b9'  # 祖霊社タスクDB
USER_ID = '4463c065-1795-49cf-a939-1b018b08e25b'  # Minami

# 日本時間
JST = ZoneInfo('Asia/Tokyo')

# 庭剪定タスク一覧（3件）
GARDEN_PRUNING_TASKS = [
    '槙の生垣剪定',
    '納骨舎前の庭剪定',
    '流し斎場周辺の庭の剪定',
]


def is_may_1st():
    """今日が5月1日かどうかを判定"""
    now = datetime.now(JST)
    return now.month == 5 and now.day == 1


def check_existing_tasks(year):
    """指定年の庭剪定タスクが既に存在するかチェック"""
    try:
        url = f"https://api.notion.com/v1/databases/{TASK_DB_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        # その年の5月1日の期限でチェック
        deadline = f"{year}-05-01"

        data = {
            "filter": {
                "and": [
                    {
                        "property": "タグ",
                        "multi_select": {"contains": "庭剪定"}
                    },
                    {
                        "property": "期限",
                        "date": {"equals": deadline}
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


def create_task(task_name, deadline):
    """Notionにタスクを作成"""
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    data = {
        'parent': {'database_id': TASK_DB_ID},
        'properties': {
            'タスク名': {
                'title': [{'text': {'content': task_name}}]
            },
            '期限': {
                'date': {'start': deadline}
            },
            'タグ': {
                'multi_select': [
                    {'name': '日常業務'},
                    {'name': '庭剪定'}
                ]
            },
            '担当者': {
                'people': [{'id': USER_ID}]
            }
        }
    }

    response = requests.post(
        f'https://api.notion.com/v1/pages',
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        return True
    else:
        print(f'❌ タスク作成失敗: {task_name}')
        print(f'   エラー: {response.text}')
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("年次庭剪定タスク自動追加スクリプト")
    print("=" * 60)

    # Notionトークンチェック
    if not NOTION_TOKEN:
        print("エラー: NOTION_TOKEN_TASK が設定されていません")
        sys.exit(1)

    # 日本時間で今日の日付を取得
    now = datetime.now(JST)
    today_str = now.strftime('%Y-%m-%d')
    year = now.year

    print(f"\n今日: {today_str}")

    # 5月1日チェック
    if not is_may_1st():
        print('ℹ️  今日は5月1日ではありません。タスク生成をスキップします。')
        return

    print(f"\n✅ 今日は5月1日です。{year}年の庭剪定タスクを生成します。")

    # 既存タスクチェック
    if check_existing_tasks(year):
        print(f"✓ {year}年の庭剪定タスクは既に追加済みです")
        return

    # タスクを順次作成
    print(f'\n📅 庭剪定タスク自動生成を開始します')
    print(f'   期限: {today_str}')
    print(f'   タスク数: {len(GARDEN_PRUNING_TASKS)}件\n')

    success_count = 0
    for i, task_name in enumerate(GARDEN_PRUNING_TASKS, 1):
        print(f'[{i}/{len(GARDEN_PRUNING_TASKS)}] {task_name}...', end=' ')

        if create_task(task_name, today_str):
            print('✅')
            success_count += 1
        else:
            print('❌')

    # 結果サマリー
    print(f'\n📊 結果: {success_count}/{len(GARDEN_PRUNING_TASKS)}件のタスクを作成しました')

    # macOS通知
    if success_count == len(GARDEN_PRUNING_TASKS):
        os.system(f'osascript -e \'display notification "{year}年の庭剪定タスク{len(GARDEN_PRUNING_TASKS)}件を自動生成しました" with title "年次庭剪定タスク自動生成"\'')
    elif success_count > 0:
        os.system(f'osascript -e \'display notification "庭剪定タスク{success_count}/{len(GARDEN_PRUNING_TASKS)}件を生成しました（一部失敗）" with title "年次庭剪定タスク自動生成"\'')
    else:
        os.system(f'osascript -e \'display notification "庭剪定タスク生成に失敗しました" with title "年次庭剪定タスク自動生成"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
