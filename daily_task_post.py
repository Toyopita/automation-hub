#!/usr/bin/env python3
"""
毎朝7時にDiscordにNotionタスク通知を投稿するスクリプト
"""
import os
import sys
import json
import discord
import asyncio
from datetime import datetime
import subprocess

# スクリプトのディレクトリ
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# .envファイルから環境変数を読み込み
def load_env_file():
    env_path = os.path.join(SCRIPT_DIR, '.env')
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

env = load_env_file()

DISCORD_TOKEN = env.get('DISCORD_TOKEN')
TASK_CHANNEL_ID = 1434389334852894911  # 📋｜タスク通知

def get_notion_tasks():
    """Notionから締切間近のタスクを取得（Node.js経由）"""
    node_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get_notion_tasks.js')

    try:
        result = subprocess.run(
            ['/usr/local/bin/node', node_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('tasks', [])
        else:
            print(f'❌ Notionタスク取得エラー: {result.stderr}')
            return []
    except Exception as e:
        print(f'❌ Notionタスク取得エラー: {e}')
        import traceback
        traceback.print_exc()
        return []

def format_task_message(tasks):
    """タスクメッセージをフォーマット"""
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    hour = today.hour
    minute = today.minute

    tasks_section = ''
    display_tasks = tasks[:5]

    for task in display_tasks:
        title = task.get('title', '（タイトルなし）')
        due_date = task.get('due_date', '')
        project_name = task.get('project_name', '日常業務')
        urgency = task.get('urgency', 'normal')

        if urgency == 'overdue':
            emoji = '🔴'
            status_text = f'期限超過 {due_date}'
        elif urgency == 'today':
            emoji = '⚠️'
            status_text = f'本日期限 {due_date}'
        else:
            emoji = '📌'
            status_text = due_date

        tasks_section += f'{emoji} {title}\n`{status_text}` | {project_name}\n\n'

    if len(tasks) > 5:
        remaining = len(tasks) - 5
        tasks_section += f'*他{remaining}件の未了タスクがあります*\n\n'
    elif len(tasks) == 0:
        tasks_section = '*締切間近のタスクはありません*\n\n'

    message = f"""📋 **締切間近のタスク**

━━━━━━━━━━━━━━━━━━━━━━━━

{tasks_section}📋 タスクDB: https://www.notion.so/1c8001601818807cb083f475eb3a07b9

━━━━━━━━━━━━━━━━━━━━━━━━
`自動送信 | {year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}`"""

    return message

async def main():
    """メイン処理"""
    print(f'🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - タスク投稿開始')

    # Notionタスク取得
    print('📋 Notionタスク取得中...')
    tasks = get_notion_tasks()
    print(f'   {len(tasks)}件のタスクを取得')

    # Discord Bot起動
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        # タスクを投稿
        task_channel = client.get_channel(TASK_CHANNEL_ID)
        if task_channel:
            # 古い投稿を削除
            print('🗑️ 古い投稿を削除中...')
            deleted_count = 0
            async for message in task_channel.history(limit=100):
                if message.author == client.user:
                    await message.delete()
                    deleted_count += 1
            print(f'✅ {deleted_count}件の古い投稿を削除')

            print('📋 タスクを投稿中...')
            task_message = format_task_message(tasks)
            await task_channel.send(task_message)
            print('✅ タスク投稿成功')
        else:
            print(f'❌ チャンネルが見つかりません: {TASK_CHANNEL_ID}')

        print('✅ タスク投稿完了')
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
