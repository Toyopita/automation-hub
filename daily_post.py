#!/usr/bin/env python3
"""
毎朝6時にDiscordに予定とタスクを投稿するスクリプト
"""
import os
import sys
import requests
from datetime import datetime, timedelta
import json

# .envファイルから環境変数を読み込み
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

env = load_env_file()

# Google Calendar MCP と Notion MCP からデータを取得する必要があるため
# この部分は後で実装します（MCPは直接Pythonから呼べないため）

# 今回は簡易版として、Webhookに直接投稿する形で実装
SCHEDULE_WEBHOOK = env.get('DISCORD_WEBHOOK_URL_SCHEDULE')
TASK_WEBHOOK = env.get('DISCORD_WEBHOOK_URL_TASK')

def post_to_discord(webhook_url, message):
    """Discord Webhookに投稿"""
    payload = {'content': message}
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code in [200, 204]:
            return True
        else:
            print(f'❌ Discord投稿失敗: {response.status_code}')
            return False
    except Exception as e:
        print(f'❌ Discord投稿エラー: {e}')
        return False

def main():
    """メイン処理"""
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    hour = today.hour
    minute = today.minute

    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[today.weekday()]
    today_str = f'{year}年{month}月{day}日（{weekday}）'

    # テスト用メッセージ
    schedule_message = f"""📅 **{today_str}の予定**

━━━━━━━━━━━━━━━━━━━━━━━━

**【六曜】** 先負

━━━━━━━━━━━━━━━━━━━━━━━━

**【本日の予定】**

*本日の予定はありません*

━━━━━━━━━━━━━━━━━━━━━━━━
`自動送信 | {year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}`"""

    task_message = f"""📋 **締切間近のタスク**

━━━━━━━━━━━━━━━━━━━━━━━━

*締切間近のタスクはありません*

📋 タスクDB: https://www.notion.so/1c8001601818807cb083f475eb3a07b9

━━━━━━━━━━━━━━━━━━━━━━━━
`自動送信 | {year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}`"""

    # Discord投稿
    print('📅 予定を投稿中...')
    if post_to_discord(SCHEDULE_WEBHOOK, schedule_message):
        print('✅ 予定投稿成功')

    print('📋 タスクを投稿中...')
    if post_to_discord(TASK_WEBHOOK, task_message):
        print('✅ タスク投稿成功')

if __name__ == '__main__':
    main()
