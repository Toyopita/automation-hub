#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tailscale認証キー更新リマインダー
90日ごとにNotionタスクDBにリマインダーを追加
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
TASK_DB_ID = '1c800160-1818-807c-b083-f475eb3a07b9'

def create_task():
    """Notionにタスクを作成"""
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }

    # 期限は70日後（キー期限90日の10日前）
    deadline = (datetime.now() + timedelta(days=70)).strftime('%Y-%m-%d')

    data = {
        'parent': {'database_id': TASK_DB_ID},
        'properties': {
            'タスク名': {
                'title': [{'text': {'content': 'Tailscale認証キー更新'}}]
            },
            '期限': {
                'date': {'start': deadline}
            }
        }
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    page_id = response.json()['id']
    print(f"[INFO] タスク作成完了: {page_id}")

    # 手順を追加
    block_url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    block_data = {
        'children': [{
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{
                    'type': 'text',
                    'text': {
                        'content': '''手順:
1. https://login.tailscale.com/admin/settings/keys
2. Generate auth key（Reusable ON、90日）
3. ~/Library/LaunchAgents/com.tailscale.autoauth.plist のキーを更新
4. launchctl unload → load で再読み込み'''
                    }
                }]
            }
        }]
    }

    requests.patch(block_url, headers=headers, json=block_data)
    print("[INFO] 手順追加完了")

if __name__ == '__main__':
    create_task()
