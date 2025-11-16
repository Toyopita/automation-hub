#!/usr/bin/env python3
"""
毎朝6時にDiscordに予定とタスクを投稿するスクリプト
既存のMCPサーバーを使用（認証不要）
"""
import os
import sys
import json
import discord
import asyncio
from datetime import datetime, timedelta
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
SCHEDULE_CHANNEL_ID = 1434368052916392076  # 📅｜今日の予定
TASK_CHANNEL_ID = 1434389334852894911      # 📋｜タスク通知
NOTION_TOKEN = env.get('NOTION_TOKEN_TASK')
NOTION_TASK_DB = '1c800160-1818-807c-b083-f475eb3a07b9'

# カレンダーID一覧
CALENDAR_IDS = [
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com',
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com',
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com',
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com',
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com',
    'izumooyashiro.osaka.takeshi@gmail.com',
    'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com',
]

CALENDAR_NAMES = {
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com': '六曜カレンダー',
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com': '祖霊社',
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com': '本社',
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com': '年祭',
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com': '冥福祭',
    'izumooyashiro.osaka.takeshi@gmail.com': 'プライベート',
    'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com': '関西イベント情報',
}

async def call_google_calendar_mcp(calendar_ids):
    """Google Calendar MCPを呼び出してイベントを取得"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    time_min = today.strftime('%Y-%m-%dT%H:%M:%S')
    time_max = tomorrow.strftime('%Y-%m-%dT%H:%M:%S')

    calendar_ids_json = json.dumps(calendar_ids)

    # Google Calendar MCPサーバーを呼び出す
    # npx を使ってMCPサーバーを起動し、リクエストを送信
    # ただし、これは複雑なので、より簡単な方法を使います

    # 実際には、Claude Code MCPツールを使っていたので、
    # subprocess でClaude Codeに指示を送る方が簡単かもしれません

    # しかし、もっとシンプルに、Node.jsスクリプトでMCPサーバーを呼び出す方法を使います
    pass

# 実は、MCPサーバーを直接Pythonから呼び出すのは複雑です
# 代わりに、Node.jsスクリプトを作成してMCPサーバーを呼び出し、
# その結果をPythonで処理する方が簡単です

async def get_calendar_events_via_node():
    """Node.jsスクリプト経由でカレンダーイベントを取得"""
    node_script = os.path.join(SCRIPT_DIR, 'get_calendar_events.js')

    if not os.path.exists(node_script):
        print('❌ get_calendar_events.js が見つかりません')
        return []

    try:
        result = subprocess.run(
            ['node', node_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('events', [])
        else:
            print(f'❌ カレンダー取得エラー: {result.stderr}')
            return []
    except Exception as e:
        print(f'❌ カレンダー取得エラー: {e}')
        return []

async def get_notion_tasks_via_node():
    """Node.jsスクリプト経由でNotionタスクを取得"""
    node_script = os.path.join(SCRIPT_DIR, 'get_notion_tasks.js')

    if not os.path.exists(node_script):
        print('❌ get_notion_tasks.js が見つかりません')
        return []

    try:
        result = subprocess.run(
            ['node', node_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('tasks', [])
        else:
            print(f'❌ タスク取得エラー: {result.stderr}')
            return []
    except Exception as e:
        print(f'❌ タスク取得エラー: {e}')
        return []

def format_schedule_message(events):
    """予定メッセージをフォーマット"""
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    hour = today.hour
    minute = today.minute

    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[today.weekday()]
    today_str = f'{year}年{month}月{day}日（{weekday}）'

    # 六曜を取得
    rokuyo = '不明'
    for event in events:
        if event.get('calendar_name') == '六曜カレンダー':
            rokuyo = event.get('title', '不明')
            break

    # 今日の予定（六曜以外）
    today_events = [e for e in events if e.get('calendar_name') != '六曜カレンダー']

    events_section = ''
    if today_events:
        for event in today_events:
            title = event.get('title', '（タイトルなし）')
            calendar_name = event.get('calendar_name', '')
            start_time = event.get('start_time', '')
            end_time = event.get('end_time', '')

            if start_time and end_time:
                events_section += f'`{start_time} - {end_time}` {title}（{calendar_name}）\n\n'
            else:
                events_section += f'{title}（{calendar_name}）\n\n'
    else:
        events_section = '*本日の予定はありません*\n\n'

    message = f"""📅 **{today_str}の予定**

━━━━━━━━━━━━━━━━━━━━━━━━

**【六曜】** {rokuyo}

━━━━━━━━━━━━━━━━━━━━━━━━

**【本日の予定】**

{events_section}━━━━━━━━━━━━━━━━━━━━━━━━
`自動送信 | {year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}`"""

    return message

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
    print(f'🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - 自動投稿開始')

    # カレンダーイベント取得
    print('📅 カレンダーイベント取得中...')
    events = await get_calendar_events_via_node()
    print(f'   {len(events)}件のイベントを取得')

    # Notionタスク取得
    print('📋 Notionタスク取得中...')
    tasks = await get_notion_tasks_via_node()
    print(f'   {len(tasks)}件のタスクを取得')

    # Discord Bot起動
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        # 予定を投稿
        schedule_channel = client.get_channel(SCHEDULE_CHANNEL_ID)
        if schedule_channel:
            print('📅 予定を投稿中...')
            schedule_message = format_schedule_message(events)
            await schedule_channel.send(schedule_message)
            print('✅ 予定投稿成功')

        # タスクを投稿
        task_channel = client.get_channel(TASK_CHANNEL_ID)
        if task_channel:
            print('📋 タスクを投稿中...')
            task_message = format_task_message(tasks)
            await task_channel.send(task_message)
            print('✅ タスク投稿成功')

        print('✅ 自動投稿完了')
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
