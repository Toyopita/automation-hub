#!/usr/bin/env python3
"""
ビルボードライブ大阪の公演スケジュールをGoogleカレンダーに自動登録

毎日10時に実行し、新規公演をカレンダーに追加
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

# Google Calendar MCP用
import subprocess

# 設定
CALENDAR_ID = '6dd1251e88a82b91cf749124fce6bb46c61f87bd3395be1685e5782bf22d91c8@group.calendar.google.com'
HISTORY_FILE = '/Users/minamitakeshi/discord-mcp-server/billboard_calendar_history.json'
LOG_FILE = '/Users/minamitakeshi/discord-mcp-server/logs/billboard_calendar.log'

# 日本時間
JST = ZoneInfo('Asia/Tokyo')


def log(message: str):
    """ログ出力"""
    timestamp = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)

    # ログファイルに追記
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')


def load_history() -> set:
    """登録済みイベントIDを読み込む"""
    if not os.path.exists(HISTORY_FILE):
        return set()

    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('registered_events', []))
    except Exception as e:
        log(f"履歴読み込みエラー: {e}")
        return set()


def save_history(registered_events: set):
    """登録済みイベントIDを保存"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'registered_events': list(registered_events),
                'updated': datetime.now(JST).isoformat()
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"履歴保存エラー: {e}")


def fetch_billboard_schedules() -> list:
    """ビルボードライブ大阪のスケジュールを取得"""
    events = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        schedule_data = None

        def handle_response(response):
            nonlocal schedule_data
            if 'get_calendar_schedules' in response.url:
                try:
                    if response.status == 200:
                        schedule_data = response.json()
                except:
                    pass

        page.on('response', handle_response)

        log("ビルボードライブ大阪のスケジュールページにアクセス中...")
        page.goto('https://www.billboard-live.com/osaka/schedules', wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(5000)

        browser.close()

        if not schedule_data:
            log("スケジュールデータの取得に失敗")
            return events

        schedules = schedule_data.get('schedules', [])
        log(f"取得したスケジュール数: {len(schedules)}")

        for item in schedules:
            sched_list = item.get('schedules', [])

            for sched in sched_list:
                if not sched or not isinstance(sched, list):
                    continue

                for show in sched:
                    if not show or not isinstance(show, dict):
                        continue

                    # 公演情報を抽出
                    event_id = show.get('event_id') or show.get('schedule_id')
                    if not event_id:
                        continue

                    title = show.get('title_name', '')
                    if not title:
                        # アーティスト名から取得
                        artists = show.get('artists', [])
                        if artists and len(artists) > 0:
                            title = artists[0].get('artist_name', '')

                    if not title:
                        continue

                    play_date = show.get('play_date', '')
                    play_open = show.get('play_open', '')
                    play_start = show.get('play_start', '')
                    play_end = show.get('play_end', '')

                    if not play_date:
                        continue

                    # アーティスト情報
                    artists = show.get('artists', [])
                    artist_names = [a.get('artist_name', '') for a in artists if a.get('artist_name')]

                    # 詳細情報
                    comment = show.get('comment1', '')
                    facility = show.get('facilityname', 'ビルボードライブ大阪')

                    # URLを生成
                    event_url = f"https://www.billboard-live.com/osaka/schedules?event_id={event_id}"

                    events.append({
                        'event_id': event_id,
                        'title': title,
                        'artists': artist_names,
                        'play_date': play_date,
                        'play_open': play_open,
                        'play_start': play_start,
                        'play_end': play_end,
                        'facility': facility,
                        'comment': comment[:500] if comment else '',
                        'url': event_url
                    })

    return events


def create_calendar_event(event: dict) -> bool:
    """Googleカレンダーにイベントを登録"""
    try:
        # 日時を設定
        play_date = event['play_date']
        play_start = event.get('play_start', '18:00')
        play_end = event.get('play_end', '21:00')

        # 終了時間が空または00:00の場合は開始から3時間後
        if not play_end or play_end == '00:00':
            start_hour = int(play_start.split(':')[0]) if play_start else 18
            end_hour = (start_hour + 3) % 24
            play_end = f"{end_hour:02d}:00"

        start_datetime = f"{play_date}T{play_start}:00"
        end_datetime = f"{play_date}T{play_end}:00"

        # イベントタイトル
        title = event['title']

        # 説明文
        description_parts = []
        if event.get('artists'):
            description_parts.append(f"アーティスト: {', '.join(event['artists'])}")
        if event.get('play_open'):
            description_parts.append(f"開場: {event['play_open']}")
        if event.get('comment'):
            description_parts.append(f"\n{event['comment']}")
        description_parts.append(f"\n{event['url']}")

        description = '\n'.join(description_parts)

        # claude CLIでカレンダーイベントを作成
        # MCP経由で直接呼び出す方法を使用
        log(f"カレンダー登録: {title} ({play_date})")

        # Node.jsスクリプトで登録
        js_code = f'''
const {{ google }} = require('googleapis');
const fs = require('fs');
const path = require('path');

async function main() {{
    const credentialsPath = path.join(process.env.HOME, 'shared-google-calendar/credentials.json');
    const tokensPath = path.join(process.env.HOME, '.config/google-calendar-mcp/tokens.json');

    const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
    const tokensData = JSON.parse(fs.readFileSync(tokensPath, 'utf8'));

    // tokens.normal形式に対応
    const tokens = tokensData.normal || tokensData;

    const {{ client_id, client_secret }} = credentials.installed || credentials.web;
    const oauth2Client = new google.auth.OAuth2(client_id, client_secret);
    oauth2Client.setCredentials(tokens);

    const calendar = google.calendar({{ version: 'v3', auth: oauth2Client }});

    const event = {{
        summary: {json.dumps(title, ensure_ascii=False)},
        location: {json.dumps(event['facility'], ensure_ascii=False)},
        description: {json.dumps(description, ensure_ascii=False)},
        start: {{
            dateTime: '{start_datetime}',
            timeZone: 'Asia/Tokyo',
        }},
        end: {{
            dateTime: '{end_datetime}',
            timeZone: 'Asia/Tokyo',
        }},
    }};

    const result = await calendar.events.insert({{
        calendarId: '{CALENDAR_ID}',
        requestBody: event,
    }});

    console.log('Event created:', result.data.htmlLink);
}}

main().catch(console.error);
'''

        # Node.jsスクリプトを実行
        result = subprocess.run(
            ['/usr/local/bin/node', '-e', js_code],
            capture_output=True,
            text=True,
            cwd='/Users/minamitakeshi/discord-mcp-server'
        )

        if result.returncode == 0:
            log(f"✅ 登録成功: {title}")
            return True
        else:
            log(f"❌ 登録失敗: {title} - {result.stderr}")
            return False

    except Exception as e:
        log(f"❌ エラー: {e}")
        return False


def main():
    """メイン処理"""
    log("=" * 50)
    log("ビルボードライブ大阪 カレンダー自動登録 開始")

    # 履歴読み込み
    registered_events = load_history()
    log(f"登録済みイベント数: {len(registered_events)}")

    # スケジュール取得
    events = fetch_billboard_schedules()
    log(f"取得した公演数: {len(events)}")

    if not events:
        log("公演情報が取得できませんでした")
        return

    # 新規イベントのみ登録
    new_events = [e for e in events if e['event_id'] not in registered_events]
    log(f"新規公演数: {len(new_events)}")

    if not new_events:
        log("新規公演はありません")
        return

    # カレンダーに登録
    success_count = 0
    for event in new_events:
        if create_calendar_event(event):
            registered_events.add(event['event_id'])
            success_count += 1

        # API制限対策
        import time
        time.sleep(1)

    # 履歴保存
    save_history(registered_events)

    log(f"登録完了: {success_count}/{len(new_events)}件")

    # macOS通知
    if success_count > 0:
        os.system(f'''osascript -e 'display notification "ビルボードライブ大阪: {success_count}件の公演を登録しました" with title "カレンダー自動登録"' ''')

    log("=" * 50)


if __name__ == "__main__":
    main()
