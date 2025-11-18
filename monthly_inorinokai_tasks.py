#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
祈りの会タスク自動生成スクリプト
毎月24日0:00に実行され、祈りの会タスク10件を自動生成する
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
PROJECT_ID = '1c900160-1818-80da-9ba3-d5fda958514f'  # 祈りの会プロジェクト

# 日本時間
JST = ZoneInfo('Asia/Tokyo')

# 祈りの会タスク一覧（10件）
INORINOKAI_TASKS = [
    '17:15に着替え',
    '神饌お清め',
    '献饌',
    'ロウソク点灯',
    '玄関とスロープドア解錠',
    '分祠長のスリッパ準備',
    '不動明王社のスポット電気点灯',
    '手水舎電気点灯',
    'ステンドグラスの照明点灯',
    'おしぼりとお茶準備',
]


def is_24th_day():
    """今日が24日かどうかを判定"""
    now = datetime.now(JST)
    return now.day == 24


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
                'multi_select': [{'name': '祈りの会'}]
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
    # 24日チェック
    # if not is_24th_day():
    #     print('ℹ️  今日は24日ではありません。タスク生成をスキップします。')
    #     return

    # 日本時間で今日の日付を取得
    now = datetime.now(JST)
    today_str = now.strftime('%Y-%m-%d')

    print(f'📅 祈りの会タスク自動生成を開始します（{today_str}）')
    print(f'   期限: {today_str}')
    print(f'   タスク数: {len(INORINOKAI_TASKS)}件\n')

    # タスクを順次作成
    success_count = 0
    for i, task_name in enumerate(INORINOKAI_TASKS, 1):
        print(f'[{i}/{len(INORINOKAI_TASKS)}] {task_name}...', end=' ')

        if create_task(task_name, today_str):
            print('✅')
            success_count += 1
        else:
            print('❌')

    # 結果サマリー
    print(f'\n📊 結果: {success_count}/{len(INORINOKAI_TASKS)}件のタスクを作成しました')

    # macOS通知
    if success_count == len(INORINOKAI_TASKS):
        os.system(f'osascript -e \'display notification "祈りの会タスク{len(INORINOKAI_TASKS)}件を自動生成しました" with title "祖霊社タスク自動生成"\'')
    elif success_count > 0:
        os.system(f'osascript -e \'display notification "祈りの会タスク{success_count}/{len(INORINOKAI_TASKS)}件を生成しました（一部失敗）" with title "祖霊社タスク自動生成"\'')
    else:
        os.system(f'osascript -e \'display notification "祈りの会タスク生成に失敗しました" with title "祖霊社タスク自動生成"\'')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
