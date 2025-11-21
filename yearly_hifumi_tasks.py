#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年次ひふみタスク自動追加スクリプト

毎年10月1日に実行され、ひふみプロジェクト関連タスク9件をNotionに自動追加する。
期限: 11月10日
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
HIFUMI_PROJECT_ID = '2ad00160-1818-815f-8359-f04889f4d9d2'  # ひふみプロジェクト

# 日本時間
JST = ZoneInfo('Asia/Tokyo')

# ひふみタスク一覧（9件）
HIFUMI_TASKS = [
    {
        'name': '寄稿依頼書の確認',
        'memo': ''
    },
    {
        'name': '責任役員用の原稿用紙準備',
        'memo': ''
    },
    {
        'name': '婦人会用の原稿用紙準備',
        'memo': ''
    },
    {
        'name': '分祠長用の原稿用紙準備',
        'memo': ''
    },
    {
        'name': '寄稿依頼メール送信',
        'memo': '青修と友誠会のみ。PDF添付すること。'
    },
    {
        'name': '新年号寄稿依頼書作成',
        'memo': ''
    },
    {
        'name': '寄稿依頼書と原稿用紙郵送',
        'memo': '角４号で切手280円。'
    },
    {
        'name': '封筒準備',
        'memo': '角４号で切手280円。'
    },
    {
        'name': '封筒用ラベル作成',
        'memo': '郵便番号、住所、氏名、敬称'
    }
]


def is_october_1st():
    """今日が10月1日かどうかを判定"""
    now = datetime.now(JST)
    return now.month == 10 and now.day == 1


def check_existing_tasks(year):
    """指定年のひふみタスクが既に存在するかチェック"""
    try:
        url = f"https://api.notion.com/v1/databases/{TASK_DB_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        # その年の11月10日の期限でチェック
        deadline = f"{year}-11-10"

        data = {
            "filter": {
                "and": [
                    {
                        "property": "プロジェクト名",
                        "relation": {"contains": HIFUMI_PROJECT_ID}
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


def create_task(task_info, deadline):
    """Notionにタスクを作成"""
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    # メモがある場合のみrich_textに追加
    memo_content = []
    if task_info['memo']:
        memo_content = [{'text': {'content': task_info['memo']}}]

    data = {
        'parent': {'database_id': TASK_DB_ID},
        'properties': {
            'タスク名': {
                'title': [{'text': {'content': task_info['name']}}]
            },
            '期限': {
                'date': {'start': deadline}
            },
            'タグ': {
                'multi_select': [
                    {'name': 'ひふみ'}
                ]
            },
            'プロジェクト名': {
                'relation': [{'id': HIFUMI_PROJECT_ID}]
            },
            'メモ': {
                'rich_text': memo_content
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
        print(f'❌ タスク作成失敗: {task_info["name"]}')
        print(f'   エラー: {response.text}')
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("年次ひふみタスク自動追加スクリプト")
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

    # 10月1日チェック
    if not is_october_1st():
        print('ℹ️  今日は10月1日ではありません。タスク生成をスキップします。')
        return

    print(f"\n✅ 今日は10月1日です。{year}年のひふみタスクを生成します。")

    # 既存タスクチェック
    if check_existing_tasks(year):
        print(f"✓ {year}年のひふみタスクは既に追加済みです")
        return

    # 期限は11月10日
    deadline = f"{year}-11-10"

    # タスクを順次作成
    print(f'\n📅 ひふみタスク自動生成を開始します')
    print(f'   期限: {deadline}')
    print(f'   タスク数: {len(HIFUMI_TASKS)}件\n')

    success_count = 0
    for i, task_info in enumerate(HIFUMI_TASKS, 1):
        print(f'[{i}/{len(HIFUMI_TASKS)}] {task_info["name"]}...', end=' ')

        if create_task(task_info, deadline):
            print('✅')
            success_count += 1
        else:
            print('❌')

    # 結果サマリー
    print(f'\n📊 結果: {success_count}/{len(HIFUMI_TASKS)}件のタスクを作成しました')

    # macOS通知
    if success_count == len(HIFUMI_TASKS):
        os.system(f'osascript -e \'display notification "{year}年のひふみタスク{len(HIFUMI_TASKS)}件を自動生成しました" with title "年次ひふみタスク自動生成"\'')
    elif success_count > 0:
        os.system(f'osascript -e \'display notification "ひふみタスク{success_count}/{len(HIFUMI_TASKS)}件を生成しました（一部失敗）" with title "年次ひふみタスク自動生成"\'')
    else:
        os.system(f'osascript -e \'display notification "ひふみタスク生成に失敗しました" with title "年次ひふみタスク自動生成"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
