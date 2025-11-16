#!/usr/bin/env python3
"""
毎朝7時にDiscordに今日の予定を投稿するスクリプト
Google Calendar MCP認証を使用
"""
import os
import sys
import json
import discord
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# スクリプトのディレクトリ
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Google Calendar MCP認証
GOOGLE_TOKEN_PATH = os.path.expanduser('~/.config/google-calendar-mcp/tokens.json')

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

# カレンダーID一覧
CALENDAR_IDS = [
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com',  # 六曜
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com',  # 祖霊社
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com',  # 本社
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com',  # 年祭
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com',  # 冥福祭
    '020de4f141e07fee4c891c7b4dfd22c730454cee4aeb28dbe21db4407f3df4c4@group.calendar.google.com',  # 御神導日
    'f4550f766a46c024206176e6f4bb036e0ec941530799d3f3209ae9d5735a334b@group.calendar.google.com',  # 三隣亡
    '01c91ee91a4b9ba0f48b4ecb215ec6e820f57ed54ca68efa9e4da31682778887@group.calendar.google.com',  # 不成就日
    'ba9a7c25efc2ea60116cb88ad6a0ceebdff5c20947bf32c7347d9ba2630c0bfe@group.calendar.google.com',  # 寒九の水
    '3c9d770c29874eef21c2d8b9cecadb6d0a2263c8f8aa0c8def5fbdca5f81a0f9@group.calendar.google.com',  # 日干支
    '68b5d9ca4fc807338b061913f260049d34d6ef36480d57201de26a39b7e065df@group.calendar.google.com',  # 宿直
    '4aaaf80646e8f62b228c281d25fef94a562a59bad4086187c7e37f3c97221e79@group.calendar.google.com',  # 土用
    'e4b184ab8be08709e7aa874f53845c52601333067a2de83965293e25f9f139c8@group.calendar.google.com',  # 彼岸
    'ja.japanese#holiday@group.v.calendar.google.com',  # 日本の祝日
]

CALENDAR_NAMES = {
    'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com': '六曜カレンダー',
    'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com': '祖霊社',
    '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com': '本社',
    '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com': '年祭',
    '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com': '冥福祭',
    '020de4f141e07fee4c891c7b4dfd22c730454cee4aeb28dbe21db4407f3df4c4@group.calendar.google.com': '御神導日',
    'f4550f766a46c024206176e6f4bb036e0ec941530799d3f3209ae9d5735a334b@group.calendar.google.com': '三隣亡',
    '01c91ee91a4b9ba0f48b4ecb215ec6e820f57ed54ca68efa9e4da31682778887@group.calendar.google.com': '不成就日',
    'ba9a7c25efc2ea60116cb88ad6a0ceebdff5c20947bf32c7347d9ba2630c0bfe@group.calendar.google.com': '寒九の水',
    '3c9d770c29874eef21c2d8b9cecadb6d0a2263c8f8aa0c8def5fbdca5f81a0f9@group.calendar.google.com': '日干支',
    '68b5d9ca4fc807338b061913f260049d34d6ef36480d57201de26a39b7e065df@group.calendar.google.com': '宿直',
    '4aaaf80646e8f62b228c281d25fef94a562a59bad4086187c7e37f3c97221e79@group.calendar.google.com': '土用',
    'e4b184ab8be08709e7aa874f53845c52601333067a2de83965293e25f9f139c8@group.calendar.google.com': '彼岸',
    'ja.japanese#holiday@group.v.calendar.google.com': '日本の祝日',
}

def get_calendar_service():
    """Google Calendar MCP認証を使用してサービスを取得（自動リフレッシュ対応）"""
    from google.auth.transport.requests import Request

    credentials_path = os.path.expanduser('~/shared-google-calendar/credentials.json')
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)

    installed = credentials_data.get('installed', {})

    with open(GOOGLE_TOKEN_PATH, 'r') as f:
        token_data = json.load(f)

    normal_token = token_data.get('normal', {})

    creds = Credentials(
        token=normal_token['access_token'],
        refresh_token=normal_token['refresh_token'],
        token_uri=installed['token_uri'],
        client_id=installed['client_id'],
        client_secret=installed['client_secret'],
        scopes=[normal_token['scope']]
    )

    # トークンが期限切れの場合は自動的にリフレッシュ
    if creds.expired and creds.refresh_token:
        try:
            print("🔄 トークンが期限切れです。自動リフレッシュを実行します...")
            creds.refresh(Request())

            # 新しいトークンを保存
            normal_token['access_token'] = creds.token
            if creds.refresh_token:
                normal_token['refresh_token'] = creds.refresh_token
            if creds.expiry:
                normal_token['expiry_date'] = int(creds.expiry.timestamp() * 1000)

            token_data['normal'] = normal_token

            with open(GOOGLE_TOKEN_PATH, 'w') as f:
                json.dump(token_data, f, indent=2)

            print(f"✅ トークンをリフレッシュしました（有効期限: {creds.expiry}）")
        except Exception as e:
            print(f"⚠️ トークンのリフレッシュに失敗しました: {e}")
            print("⚠️ 手動で再認証が必要です")
            raise

    return build('calendar', 'v3', credentials=creds)

def get_today_events():
    """今日のカレンダーイベントを取得"""
    service = get_calendar_service()

    # JSTで今日の日付を取得
    jst = ZoneInfo("Asia/Tokyo")
    now_jst = datetime.now(jst)
    today = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    # UTCに変換してISO形式に
    time_min = today.astimezone(ZoneInfo("UTC")).isoformat()
    time_max = tomorrow.astimezone(ZoneInfo("UTC")).isoformat()

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

                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                # 終日イベントの場合、今日の日付と一致するかチェック
                if 'date' in event['start']:
                    start_date = event['start']['date']
                    today_str = today.strftime('%Y-%m-%d')
                    # 終日イベントの開始日が今日であることを確認
                    if start_date != today_str:
                        continue

                all_events.append({
                    'title': event.get('summary', '（タイトルなし）'),
                    'start': start,
                    'end': end,
                    'calendar_name': calendar_name,
                })
        except Exception as e:
            print(f'⚠️ カレンダー取得エラー ({calendar_id}): {e}')

    return all_events

def format_schedule_message(events):
    """予定メッセージをフォーマット"""
    jst = ZoneInfo("Asia/Tokyo")
    today = datetime.now(jst)
    year = today.year
    month = today.month
    day = today.day
    hour = today.hour
    minute = today.minute

    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[today.weekday()]
    today_str = f'{year}年{month}月{day}日（{weekday}）'

    # 祝日
    holiday = None
    for event in events:
        if event['calendar_name'] == '日本の祝日':
            holiday = event['title']
            break

    # 六曜
    rokuyo = '不明'
    for event in events:
        if event['calendar_name'] == '六曜カレンダー':
            rokuyo = event['title']
            break

    # 日干支
    nikkanshi = '不明'
    for event in events:
        if event['calendar_name'] == '日干支':
            nikkanshi = event['title']
            break

    # 不成就日
    fujoju = None
    for event in events:
        if event['calendar_name'] == '不成就日':
            fujoju = event['title']
            break

    # 三隣亡
    sanrinbo = None
    for event in events:
        if event['calendar_name'] == '三隣亡':
            sanrinbo = event['title']
            break

    # 土用
    doyo = None
    for event in events:
        if event['calendar_name'] == '土用':
            doyo = event['title']
            break

    # 彼岸
    higan = None
    for event in events:
        if event['calendar_name'] == '彼岸':
            higan = event['title']
            break

    # 今日の予定（特別扱いするもの以外）
    special_calendars = ['六曜カレンダー', '日干支', '不成就日', '三隣亡', '日本の祝日', '土用', '彼岸']
    today_events = [e for e in events if e['calendar_name'] not in special_calendars]

    events_section = ''
    if today_events:
        for event in today_events:
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

    # 特別なカレンダー情報
    special_info = ""
    if holiday:
        special_info += f"**【祝　日】** {holiday}\n"

    special_info += f"**【六　曜】** {rokuyo}\n"
    special_info += f"**【日干支】** {nikkanshi}\n"

    if fujoju:
        special_info += f"**【不成就日】** {fujoju}\n"
    if sanrinbo:
        special_info += f"**【三隣亡】** {sanrinbo}\n"

    if doyo:
        special_info += f"**【土　用】** {doyo}\n"
    if higan:
        special_info += f"**【彼　岸】** {higan}\n"

    message = f"""📅 **{today_str}の予定**

━━━━━━━━━━━━━━━━━━━━━━━━

{special_info}
**【本日の予定】**

{events_section}━━━━━━━━━━━━━━━━━━━━━━━━
`自動送信 | {year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}`"""

    return message

async def main():
    """メイン処理"""
    print(f'🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - 予定投稿開始')

    # カレンダーイベント取得
    print('📅 カレンダーイベント取得中...')
    events = get_today_events()
    print(f'   {len(events)}件のイベントを取得')

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
            # 古い投稿を削除
            print('🗑️ 古い投稿を削除中...')
            deleted_count = 0
            async for message in schedule_channel.history(limit=100):
                if message.author == client.user:
                    await message.delete()
                    deleted_count += 1
            print(f'✅ {deleted_count}件の古い投稿を削除')

            print('📅 予定を投稿中...')
            schedule_message = format_schedule_message(events)
            await schedule_channel.send(schedule_message)
            print('✅ 予定投稿成功')

        print('✅ 予定投稿完了')
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
