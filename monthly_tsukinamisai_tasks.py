#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月次祭タスク自動生成スクリプト
毎月末日0:00に実行され、翌月1日用の月次祭タスク13件を自動生成する
"""

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# Notion API設定
NOTION_TOKEN = os.getenv('NOTION_TOKEN_TASK')
NOTION_API_URL = 'https://api.notion.com/v1'
NOTION_VERSION = '2022-06-28'

# データベースID
TASK_DB_ID = '1c800160-1818-807c-b083-f475eb3a07b9'  # 祖霊社タスクDB
PROJECT_ID = '23e00160-1818-80f2-b1c8-e5306b7e0a80'  # 月次祭プロジェクト

# 日本時間
JST = ZoneInfo('Asia/Tokyo')

# 月次祭タスク一覧（16件）
# 辞書形式: {'name': タスク名, 'content': ページ内コンテンツ（オプション）}
TSUKINAMISAI_TASKS = [
    {'name': '分祠長用玉串準備'},
    {'name': 'プレート掲示'},
    {'name': '命日祭の看板設置'},
    {'name': '冥福祭用神饌入替'},
    {'name': '祝詞座の日拝詞撤去'},
    {'name': '案入れ替え'},
    {'name': '高坏5台準備', 'content': '金剛不動明王社'},
    {'name': '命日祭申込書準備'},
    {'name': '皿など陶器類準備'},
    {'name': '分祠長用玉串仮案準備'},
    {'name': '分祠長用スリッパ準備'},
    {'name': '初穂料記帳用の机設置'},
    {'name': '日供用神饌入替'},
    {'name': '榊作成'},
    {'name': '玉串作成'},
    {'name': 'ろうそく台増設'},
]


def is_last_day_of_month():
    """今日が月末かどうかを判定"""
    now = datetime.now(JST)
    tomorrow = now + timedelta(days=1)

    # 明日が1日なら今日は月末
    return tomorrow.day == 1


def create_task(task_name, deadline, page_content=None):
    """Notionにタスクを作成"""
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_VERSION
    }

    data = {
        'parent': {'database_id': TASK_DB_ID},
        'properties': {
            'タスク名': {
                'title': [{'text': {'content': task_name}}]
            },
            'プロジェクト名': {
                'relation': [{'id': PROJECT_ID}]
            },
            '期限': {
                'date': {'start': deadline}
            },
            'タグ': {
                'multi_select': [{'name': '月次祭'}]
            }
        }
    }

    # ページ内コンテンツがある場合は追加
    if page_content:
        data['children'] = [
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [{'type': 'text', 'text': {'content': page_content}}]
                }
            }
        ]

    response = requests.post(
        f'{NOTION_API_URL}/pages',
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
    # 月末チェック
    if not is_last_day_of_month():
        print('ℹ️  今日は月末ではありません。タスク生成をスキップします。')
        return

    # 日本時間で今日の日付を取得
    now = datetime.now(JST)
    today_str = now.strftime('%Y-%m-%d')

    print(f'📅 月次祭タスク自動生成を開始します（{today_str}）')
    print(f'   期限: {today_str}')
    print(f'   タスク数: {len(TSUKINAMISAI_TASKS)}件\n')

    # タスクを順次作成
    success_count = 0
    for i, task in enumerate(TSUKINAMISAI_TASKS, 1):
        task_name = task['name']
        page_content = task.get('content')
        print(f'[{i}/{len(TSUKINAMISAI_TASKS)}] {task_name}...', end=' ')

        if create_task(task_name, today_str, page_content):
            print('✅')
            success_count += 1
        else:
            print('❌')

    # 結果サマリー
    print(f'\n📊 結果: {success_count}/{len(TSUKINAMISAI_TASKS)}件のタスクを作成しました')

    # macOS通知
    if success_count == len(TSUKINAMISAI_TASKS):
        os.system(f'osascript -e \'display notification "月次祭タスク{len(TSUKINAMISAI_TASKS)}件を自動生成しました" with title "祖霊社タスク自動生成"\'')
    elif success_count > 0:
        os.system(f'osascript -e \'display notification "月次祭タスク{success_count}/{len(TSUKINAMISAI_TASKS)}件を生成しました（一部失敗）" with title "祖霊社タスク自動生成"\'')
    else:
        os.system(f'osascript -e \'display notification "月次祭タスク生成に失敗しました" with title "祖霊社タスク自動生成"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
