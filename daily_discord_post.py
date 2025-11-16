#!/usr/bin/env python3
"""
毎朝6時にDiscordに予定とタスクを投稿するスクリプト（完全自動版）
"""
import os
import sys
import pickle
import requests
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from notion_client import Client

# スクリプトのディレクトリ
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Google Calendar API設定
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
TOKEN_PATH = os.path.join(SCRIPT_DIR, 'token.pickle')
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, 'credentials.json')

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

SCHEDULE_WEBHOOK = env.get('DISCORD_WEBHOOK_URL_SCHEDULE')
TASK_WEBHOOK = env.get('DISCORD_WEBHOOK_URL_TASK')
NOTION_TOKEN = env.get('NOTION_TOKEN_TASK')
NOTION_TASK_DB = '1c800160-1818-807c-b083-f475eb3a07b9'

# カレンダーID一覧（GASのコードから取得）
CALENDAR_IDS = [
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com',  # 六曜
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com',  # 祖霊社
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com',  # 本社
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com',  # 年祭
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com',  # 冥福祭
    'izumooyashiro.osaka.takeshi@gmail.com',  # プライベート
    'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com',  # 関西イベント
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

def get_calendar_service():
    """Google Calendar APIサービスを取得"""
    creds = None

    # トークンファイルがあれば読み込む
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # 認証情報がないか期限切れの場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print('❌ credentials.jsonが見つかりません')
                print(f'   {CREDENTIALS_PATH} に配置してください')
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # トークンを保存
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)

def get_today_events():
    """今日のカレンダーイベントを取得"""
    service = get_calendar_service()

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    time_min = today.isoformat() + 'Z'
    time_max = tomorrow.isoformat() + 'Z'

    all_events = []

    for calendar_id in CALENDAR_IDS:
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            for event in events:
                calendar_name = CALENDAR_NAMES.get(calendar_id, calendar_id)

                # 開始時刻
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                all_events.append({
                    'title': event.get('summary', '（タイトルなし）'),
                    'start': start,
                    'end': end,
                    'calendar_name': calendar_name,
                })
        except Exception as e:
            print(f'⚠️ カレンダー取得エラー ({calendar_id}): {e}')

    return all_events

def get_notion_tasks():
    """Notionから締切間近のタスクを取得"""
    notion = Client(auth=NOTION_TOKEN)

    # 1週間後まで
    one_week_later = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    try:
        results = notion.databases.query(
            database_id=NOTION_TASK_DB,
            filter={
                'and': [
                    {'property': '進捗', 'status': {'does_not_equal': '完了'}},
                    {'property': '期限', 'date': {'on_or_before': one_week_later}}
                ]
            },
            sorts=[{'property': '期限', 'direction': 'ascending'}]
        )
        return results.get('results', [])
    except Exception as e:
        print(f'❌ Notionタスク取得エラー: {e}')
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
        if event['calendar_name'] == '六曜カレンダー':
            rokuyo = event['title']
            break

    # 今日の予定（六曜以外）
    today_events = [e for e in events if e['calendar_name'] != '六曜カレンダー']

    events_section = ''
    if today_events:
        for event in today_events:
            # 時刻をフォーマット
            try:
                if 'T' in event['start']:
                    start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
                    start_time = start_dt.strftime('%H:%M')
                    end_time = end_dt.strftime('%H:%M')
                    events_section += f'`{start_time} - {end_time}` {event["title"]}（{event["calendar_name"]}）\n\n'
                else:
                    events_section += f'{event["title"]}（{event["calendar_name"]}）\n\n'
            except:
                events_section += f'{event["title"]}（{event["calendar_name"]}）\n\n'
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

def get_project_name(notion, project_id):
    """プロジェクト名を取得"""
    try:
        page = notion.pages.retrieve(page_id=project_id)
        title_prop = page['properties'].get('プロジェクト名', {})
        if title_prop.get('title'):
            return title_prop['title'][0]['plain_text']
    except:
        pass
    return '日常業務'

def format_task_message(tasks):
    """タスクメッセージをフォーマット"""
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    hour = today.hour
    minute = today.minute

    notion = Client(auth=NOTION_TOKEN)

    tasks_section = ''
    display_tasks = tasks[:5]

    for task in display_tasks:
        # タスク名
        title_prop = task['properties'].get('タスク名', {})
        title = title_prop.get('title', [{}])[0].get('plain_text', '（タイトルなし）')

        # 期限
        due_prop = task['properties'].get('期限', {})
        due_date_str = due_prop.get('date', {}).get('start', '')

        if due_date_str:
            due_date = datetime.fromisoformat(due_date_str.split('T')[0])
            diff_days = (due_date.date() - today.date()).days

            due_month = due_date.month
            due_day = due_date.day
            due_date_fmt = f'{due_month}/{due_day}'

            # プロジェクト名
            relation_prop = task['properties'].get('プロジェクト名', {})
            relations = relation_prop.get('relation', [])

            project_name = '日常業務'
            if relations:
                project_id = relations[0]['id']
                project_name = get_project_name(notion, project_id)

            # 緊急度
            if diff_days < 0:
                emoji = '🔴'
                status_text = f'期限超過 {due_date_fmt}'
            elif diff_days == 0:
                emoji = '⚠️'
                status_text = f'本日期限 {due_date_fmt}'
            else:
                emoji = '📌'
                status_text = due_date_fmt

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
    print(f'🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - 自動投稿開始')

    # カレンダーイベント取得
    print('📅 カレンダーイベント取得中...')
    events = get_today_events()
    print(f'   {len(events)}件のイベントを取得')

    # Notionタスク取得
    print('📋 Notionタスク取得中...')
    tasks = get_notion_tasks()
    print(f'   {len(tasks)}件のタスクを取得')

    # 予定を投稿
    print('📅 予定を投稿中...')
    schedule_message = format_schedule_message(events)
    if post_to_discord(SCHEDULE_WEBHOOK, schedule_message):
        print('✅ 予定投稿成功')

    # タスクを投稿
    print('📋 タスクを投稿中...')
    task_message = format_task_message(tasks)
    if post_to_discord(TASK_WEBHOOK, task_message):
        print('✅ タスク投稿成功')

    print('✅ 自動投稿完了')

if __name__ == '__main__':
    main()
