#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年祭タスク自動追加スクリプト

毎日0:00に実行され、翌日（明日）に年祭がある場合、
今日を期限として12タスクをNotionに自動追加する。
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# .envファイルから環境変数を読み込む
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# 環境変数から取得
NOTION_TOKEN = os.environ.get('NOTION_TOKEN_TASK')
NENSAI_PROJECT_ID = "d095a904-59d0-494a-b91e-af83c310dffa"
TASK_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"
USER_ID = "4463c065-1795-49cf-a939-1b018b08e25b"  # Minami
NENSAI_CALENDAR_ID = "40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com"

# Google Calendar認証
GOOGLE_TOKEN_PATH = os.path.expanduser('~/.config/google-calendar-mcp/tokens.json')
CREDENTIALS_PATH = os.path.expanduser('~/shared-google-calendar/credentials.json')

# 追加するタスクリスト
TASKS = [
    "年祭の預り金を前日に処理する",
    "玉串仮案の整理",
    "玉串案の内容整理",
    "厚畳",
    "祝詞仮案の整理",
    "祓詞用の願い主名簿",
    "祝詞案の整理",
    "年祭祓詞",
    "年祭の読み上げ芳名簿の整理",
    "年祭の祝詞を唱える",
    "参列者用玉串",
    "斎主用玉串"
]


def get_calendar_service():
    """Google Calendar APIサービスを取得"""
    with open(CREDENTIALS_PATH, 'r') as f:
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
        creds.refresh(Request())

    return build('calendar', 'v3', credentials=creds)


def get_tomorrow_nensai_events():
    """Googleカレンダーから明日の年祭イベントを取得"""
    try:
        service = get_calendar_service()

        # 日本時間で明日の0:00から23:59まで
        jst = ZoneInfo('Asia/Tokyo')
        now = datetime.now(jst)
        tomorrow = now + timedelta(days=1)

        # 明日の0:00
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        # 明日の23:59
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)

        time_min = tomorrow_start.isoformat()
        time_max = tomorrow_end.isoformat()

        events_result = service.events().list(
            calendarId=NENSAI_CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            timeZone='Asia/Tokyo'
        ).execute()

        events = []
        for item in events_result.get('items', []):
            summary = item.get('summary', '')
            if '年祭' in summary:
                start = item['start'].get('dateTime', item['start'].get('date'))
                event_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if event_date.tzinfo is None:
                    event_date = event_date.replace(tzinfo=jst)

                events.append({
                    'summary': summary,
                    'start': event_date,
                    'id': item.get('id')
                })

        return events

    except Exception as e:
        print(f"エラー: {e}")
        return []


def check_existing_tasks(deadline):
    """指定期限のタスクが既に存在するかチェック"""
    try:
        url = "https://api.notion.com/v1/databases/{}/query".format(TASK_DB_ID)
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        data = {
            "filter": {
                "and": [
                    {
                        "property": "プロジェクト名",
                        "relation": {"contains": NENSAI_PROJECT_ID}
                    },
                    {
                        "property": "期限",
                        "date": {"equals": deadline}
                    }
                ]
            }
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            results = response.json().get('results', [])
            return len(results) > 0
        else:
            print(f"警告: タスク検索失敗: {response.text}")
            return False

    except Exception as e:
        print(f"警告: タスク検索エラー: {e}")
        return False


def add_task_to_notion(task_name, deadline):
    """Notionにタスクを追加"""
    try:
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        data = {
            "parent": {"database_id": TASK_DB_ID},
            "properties": {
                "タスク名": {"title": [{"text": {"content": task_name}}]},
                "プロジェクト名": {"relation": [{"id": NENSAI_PROJECT_ID}]},
                "期限": {"date": {"start": deadline}},
                "タグ": {"multi_select": [{"name": "年祭"}]},
                "担当者": {"people": [{"id": USER_ID}]}
            }
        }

        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200

    except Exception as e:
        print(f"  エラー: {task_name} の追加中にエラー: {e}")
        return False


def add_tasks_for_tomorrow_event(event_date, event_name):
    """明日の年祭用のタスクを今日を期限として追加"""
    # 1日の年祭はスキップ
    if event_date.day == 1:
        print(f"× {event_name} ({event_date.strftime('%Y-%m-%d')}) は1日のためスキップ")
        return 0

    # 今日を期限とする（日本時間）
    jst = ZoneInfo('Asia/Tokyo')
    today = datetime.now(jst)
    deadline = today.strftime('%Y-%m-%d')

    # 既にタスクが存在するかチェック
    if check_existing_tasks(deadline):
        print(f"✓ {event_name} ({event_date.strftime('%Y-%m-%d')}) のタスクは既に追加済み")
        return 0

    print(f"→ 明日の {event_name} ({event_date.strftime('%Y-%m-%d')}) のタスクを追加中...")
    print(f"   期限: {deadline}")

    added_count = 0
    for task_name in TASKS:
        if add_task_to_notion(task_name, deadline):
            added_count += 1

    print(f"  ✓ {added_count}/{len(TASKS)} タスクを追加しました")
    return added_count


def main():
    print("=" * 60)
    print("年祭タスク自動追加スクリプト")
    print("=" * 60)

    # Notionトークンチェック
    if not NOTION_TOKEN:
        print("エラー: NOTION_TOKEN_TASK が設定されていません")
        sys.exit(1)

    # 日本時間で今日と明日の日付を表示
    jst = ZoneInfo('Asia/Tokyo')
    now = datetime.now(jst)
    tomorrow = now + timedelta(days=1)
    print(f"\n今日: {now.strftime('%Y-%m-%d (%A)')}")
    print(f"明日: {tomorrow.strftime('%Y-%m-%d (%A)')}")

    # 明日の年祭イベント取得
    print("\n[1] 明日の年祭イベントを確認中...")
    events = get_tomorrow_nensai_events()

    if not events:
        print("  ℹ️  明日に年祭はありません。タスク生成をスキップします。")
        return

    print(f"  ✓ 明日に{len(events)}件の年祭イベントがあります")

    # 各イベントに対してタスク追加
    print("\n[2] タスクを追加中...")
    total_added = 0

    for event in events:
        added = add_tasks_for_tomorrow_event(event['start'], event['summary'])
        total_added += added

    # 結果通知
    print("\n" + "=" * 60)
    if total_added > 0:
        print(f"完了: {total_added}件のタスクを追加しました")
    else:
        print("タスクは既に追加済みです")
    print("=" * 60)

    # macOS通知
    if total_added > 0:
        import subprocess
        subprocess.run([
            'osascript', '-e',
            f'display notification "明日の年祭用タスク{total_added}件を追加しました" with title "年祭タスク自動追加"'
        ])


if __name__ == '__main__':
    main()
