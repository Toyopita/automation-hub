#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金剛不動明王月次祭タスク自動生成スクリプト
毎月27日0:00に実行され、金剛不動明王月次祭タスク5件を自動生成する
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
PROJECT_ID = '1e200160-1818-80dd-9ddb-f2631b23e963'  # 金剛不動明王月次祭プロジェクト

# 日本時間
JST = ZoneInfo('Asia/Tokyo')

# 金剛不動明王月次祭タスク一覧（5件）
FUDOUMYOUOU_TASKS = [
    '幕取り付け',
    'おさがり準備',
    '高坏6台',
    '案入れ替え',
    '酒と塩入れ替え',
]


def is_27th_day():
    """今日が27日かどうかを判定"""
    now = datetime.now(JST)
    return now.day == 27


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
                'multi_select': [{'name': '金剛不動明王月次祭'}]
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
    # 27日チェック
    if not is_27th_day():
        print('ℹ️  今日は27日ではありません。タスク生成をスキップします。')
        return

    # 日本時間で今日の日付を取得
    now = datetime.now(JST)
    today_str = now.strftime('%Y-%m-%d')

    print(f'📅 金剛不動明王月次祭タスク自動生成を開始します（{today_str}）')
    print(f'   期限: {today_str}')
    print(f'   タスク数: {len(FUDOUMYOUOU_TASKS)}件\n')

    # タスクを順次作成
    success_count = 0
    for i, task_name in enumerate(FUDOUMYOUOU_TASKS, 1):
        print(f'[{i}/{len(FUDOUMYOUOU_TASKS)}] {task_name}...', end=' ')

        if create_task(task_name, today_str):
            print('✅')
            success_count += 1
        else:
            print('❌')

    # 結果サマリー
    print(f'\n📊 結果: {success_count}/{len(FUDOUMYOUOU_TASKS)}件のタスクを作成しました')

    # macOS通知
    if success_count == len(FUDOUMYOUOU_TASKS):
        os.system(f'osascript -e \'display notification "金剛不動明王月次祭タスク{len(FUDOUMYOUOU_TASKS)}件を自動生成しました" with title "祖霊社タスク自動生成"\'')
    elif success_count > 0:
        os.system(f'osascript -e \'display notification "金剛不動明王月次祭タスク{success_count}/{len(FUDOUMYOUOU_TASKS)}件を生成しました（一部失敗）" with title "祖霊社タスク自動生成"\'')
    else:
        os.system(f'osascript -e \'display notification "金剛不動明王月次祭タスク生成に失敗しました" with title "祖霊社タスク自動生成"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
