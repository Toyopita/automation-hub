#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感謝祭タスク自動生成スクリプト（テスト版）
14日チェックをバイパスして即座にタスクを生成
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN_TASK')
NOTION_API_URL = 'https://api.notion.com/v1'
NOTION_VERSION = '2022-06-28'

TASK_DB_ID = '1c800160-1818-807c-b083-f475eb3a07b9'
PROJECT_ID = '1e500160-1818-81d0-bfb4-e1406c74949e'  # 感謝祭

JST = ZoneInfo('Asia/Tokyo')

KANSHASAI_TASKS = [
    '分祠長用玉串準備',
    'プレート掲示',
    '命日祭の看板設置',
    '冥福祭用神饌入替',
    '祝詞座の日拝詞撤去',
    '案入れ替え',
    '高坏5台準備',
    '命日祭申込書準備',
    '皿など陶器類準備',
    '分祠長用玉串仮案準備',
    '分祠長用スリッパ準備',
    '初穂料記帳用の机設置',
    '日供用神饌入替',
]


def create_task(task_name, deadline):
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
                'multi_select': [{'name': '感謝祭'}]
            }
        }
    }

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
    now = datetime.now(JST)
    today_str = now.strftime('%Y-%m-%d')

    print(f'🧪 テスト実行: 感謝祭タスク自動生成（{today_str}）')
    print(f'   期限: {today_str}')
    print(f'   タスク数: {len(KANSHASAI_TASKS)}件\n')

    success_count = 0
    for i, task_name in enumerate(KANSHASAI_TASKS, 1):
        print(f'[{i}/{len(KANSHASAI_TASKS)}] {task_name}...', end=' ')

        if create_task(task_name, today_str):
            print('✅')
            success_count += 1
        else:
            print('❌')

    print(f'\n📊 結果: {success_count}/{len(KANSHASAI_TASKS)}件のタスクを作成しました')

    if success_count == len(KANSHASAI_TASKS):
        os.system(f'osascript -e \'display notification "テスト成功: 感謝祭タスク{len(KANSHASAI_TASKS)}件を作成しました" with title "祖霊社タスク自動生成テスト"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
