#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感謝祭タスク自動生成スクリプト
毎月14日0:00に実行され、感謝祭タスク13件を自動生成する
"""

import os
import sys
from datetime import datetime
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
PROJECT_ID = '1e500160-1818-81d0-bfb4-e1406c74949e'  # 感謝祭プロジェクト

# 日本時間
JST = ZoneInfo('Asia/Tokyo')

# 感謝祭タスク一覧（16件）
# 辞書形式: {'name': タスク名, 'content': ページ内コンテンツ（オプション）}
KANSHASAI_TASKS = [
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


def is_14th_day():
    """今日が14日かどうかを判定"""
    now = datetime.now(JST)
    return now.day == 14


def create_task(task_name, deadline):
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
    """メイン処理"""
    # 14日チェック
    if not is_14th_day():
        print('ℹ️  今日は14日ではありません。タスク生成をスキップします。')
        return

    # 日本時間で今日の日付を取得
    now = datetime.now(JST)
    today_str = now.strftime('%Y-%m-%d')

    print(f'📅 感謝祭タスク自動生成を開始します（{today_str}）')
    print(f'   期限: {today_str}')
    print(f'   タスク数: {len(KANSHASAI_TASKS)}件\n')

    # タスクを順次作成
    success_count = 0
    for i, task_name in enumerate(KANSHASAI_TASKS, 1):
        print(f'[{i}/{len(KANSHASAI_TASKS)}] {task_name}...', end=' ')

        if create_task(task_name, today_str):
            print('✅')
            success_count += 1
        else:
            print('❌')

    # 結果サマリー
    print(f'\n📊 結果: {success_count}/{len(KANSHASAI_TASKS)}件のタスクを作成しました')

    # macOS通知
    if success_count == len(KANSHASAI_TASKS):
        os.system(f'osascript -e \'display notification "感謝祭タスク{len(KANSHASAI_TASKS)}件を自動生成しました" with title "祖霊社タスク自動生成"\'')
    elif success_count > 0:
        os.system(f'osascript -e \'display notification "感謝祭タスク{success_count}/{len(KANSHASAI_TASKS)}件を生成しました（一部失敗）" with title "祖霊社タスク自動生成"\'')
    else:
        os.system(f'osascript -e \'display notification "感謝祭タスク生成に失敗しました" with title "祖霊社タスク自動生成"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
