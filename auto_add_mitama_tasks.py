#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
御霊鎮めタスク自動追加スクリプト

毎日0:00に実行され、明日から2ヶ月先までに御霊鎮めがある場合、
イベント日付から逆算してタスクをNotionに自動追加する。

タスク期限ルール:
- 開催24日前: 1件（撤饌在庫確認）
- 開催5日前: 13件
- 開催前日: 9件
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
TASK_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"
PROJECT_DB_ID = "1c800160-1818-8004-9609-c1250a7e3478"
USER_ID = "4463c065-1795-49cf-a939-1b018b08e25b"  # Minami
SORYO_CALENDAR_ID = "cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com"

# Google Calendar認証
GOOGLE_TOKEN_PATH = os.path.expanduser('~/.config/google-calendar-mcp/tokens.json')
CREDENTIALS_PATH = os.path.expanduser('~/shared-google-calendar/credentials.json')

# 追加するタスクリスト（期限別）
# 開催24日前（1件）
TASKS_24_DAYS_BEFORE = [
    "撤饌在庫確認"
]

# 開催5日前（13件）
TASKS_5_DAYS_BEFORE = [
    "御霊鎮めの習礼",
    "霊璽確認",
    "木の霊璽作成",
    "祓詞準備",
    "祭祀録作成",
    "式次第確認",
    "祭員確認",
    "玉串名簿作成",
    "霊璽用の小さい榊準備",
    "分祠長用衣装準備",
    "祭員用衣装準備",
    "祭祀録ファイルの更新",
    "受付用名簿一覧表作成"
]

# 開催前日（9件）
TASKS_1_DAY_BEFORE = [
    "白マスク準備",
    "神納書準備",
    "神饌納品の確認",
    "白手袋準備",
    "祝詞作成",
    "音響遠隔操作の動作確認",
    "照明遠隔操作の動作確認",
    "霊璽殿内モップがけ",
    "乾物準備"
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


def get_upcoming_mitama_events():
    """Googleカレンダーから明日から2ヶ月先までの御霊鎮めイベントを取得"""
    try:
        service = get_calendar_service()

        # 日本時間で明日から2ヶ月先まで
        jst = ZoneInfo('Asia/Tokyo')
        now = datetime.now(jst)
        tomorrow = now + timedelta(days=1)
        two_months_later = now + timedelta(days=60)

        # 明日の0:00
        search_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        # 2ヶ月後の23:59
        search_end = two_months_later.replace(hour=23, minute=59, second=59, microsecond=999999)

        time_min = search_start.isoformat()
        time_max = search_end.isoformat()

        events_result = service.events().list(
            calendarId=SORYO_CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            timeZone='Asia/Tokyo'
        ).execute()

        events = []
        for item in events_result.get('items', []):
            summary = item.get('summary', '')
            if '御霊鎮め' in summary:
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
        import traceback
        traceback.print_exc()
        return []


def find_project_by_date(event_date):
    """指定日付の御霊鎮めプロジェクトを検索"""
    try:
        url = f"https://api.notion.com/v1/databases/{PROJECT_DB_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        # まず御霊鎮めプロジェクトを全件取得
        data = {
            "filter": {
                "property": "プロジェクト名",
                "title": {"contains": "御霊鎮め"}
            }
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            results = response.json().get('results', [])
            target_date = event_date.strftime('%Y-%m-%d')

            # 各プロジェクトの期間をチェック
            for project in results:
                period = project['properties'].get('期間', {}).get('date')
                if period:
                    start_date = period.get('start', '')
                    # 日付が一致するか確認（時刻部分は無視）
                    if start_date.startswith(target_date):
                        return project['id']
        return None

    except Exception as e:
        print(f"警告: プロジェクト検索エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_project(event_date):
    """御霊鎮めプロジェクトを作成"""
    try:
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        data = {
            "parent": {"database_id": PROJECT_DB_ID},
            "properties": {
                "プロジェクト名": {"title": [{"text": {"content": "御霊鎮め"}}]},
                "期間": {"date": {"start": event_date.strftime('%Y-%m-%d')}},
                "担当者": {"people": [{"id": USER_ID}]}
            }
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['id']
        else:
            print(f"エラー: プロジェクト作成失敗: {response.text}")
            return None

    except Exception as e:
        print(f"エラー: プロジェクト作成中にエラー: {e}")
        return None


def check_existing_tasks(project_id, deadline):
    """指定プロジェクト・期限のタスクが既に存在するかチェック"""
    try:
        url = f"https://api.notion.com/v1/databases/{TASK_DB_ID}/query"
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
                        "relation": {"contains": project_id}
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


def add_task_to_notion(task_name, project_id, deadline):
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
                "プロジェクト名": {"relation": [{"id": project_id}]},
                "期限": {"date": {"start": deadline}},
                "タグ": {"multi_select": [{"name": "御霊鎮め"}]},
                "担当者": {"people": [{"id": USER_ID}]}
            }
        }

        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200

    except Exception as e:
        print(f"  エラー: {task_name} の追加中にエラー: {e}")
        return False


def add_tasks_for_event(event_date, event_name):
    """御霊鎮めイベント用のタスクを追加"""
    print(f"\n→ {event_name} ({event_date.strftime('%Y-%m-%d')}) の処理中...")

    # プロジェクト検索または作成
    project_id = find_project_by_date(event_date)
    if project_id:
        print(f"  ✓ プロジェクトは既に存在します")
    else:
        print(f"  → プロジェクトを作成中...")
        project_id = create_project(event_date)
        if not project_id:
            print(f"  ✗ プロジェクト作成失敗")
            return 0
        print(f"  ✓ プロジェクト作成完了")

    # タスク追加（期限別に処理）
    total_added = 0
    jst = ZoneInfo('Asia/Tokyo')

    # 開催24日前のタスク
    deadline_24 = (event_date - timedelta(days=24)).strftime('%Y-%m-%d')
    if not check_existing_tasks(project_id, deadline_24):
        print(f"  → 開催24日前タスク追加中（期限: {deadline_24}）...")
        for task_name in TASKS_24_DAYS_BEFORE:
            if add_task_to_notion(task_name, project_id, deadline_24):
                total_added += 1
    else:
        print(f"  ✓ 開催24日前タスクは既に追加済み")

    # 開催5日前のタスク
    deadline_5 = (event_date - timedelta(days=5)).strftime('%Y-%m-%d')
    if not check_existing_tasks(project_id, deadline_5):
        print(f"  → 開催5日前タスク追加中（期限: {deadline_5}）...")
        for task_name in TASKS_5_DAYS_BEFORE:
            if add_task_to_notion(task_name, project_id, deadline_5):
                total_added += 1
    else:
        print(f"  ✓ 開催5日前タスクは既に追加済み")

    # 開催前日のタスク
    deadline_1 = (event_date - timedelta(days=1)).strftime('%Y-%m-%d')
    if not check_existing_tasks(project_id, deadline_1):
        print(f"  → 開催前日タスク追加中（期限: {deadline_1}）...")
        for task_name in TASKS_1_DAY_BEFORE:
            if add_task_to_notion(task_name, project_id, deadline_1):
                total_added += 1
    else:
        print(f"  ✓ 開催前日タスクは既に追加済み")

    if total_added > 0:
        print(f"  ✓ {total_added}件のタスクを追加しました")

    return total_added


def main():
    print("=" * 60)
    print("御霊鎮めタスク自動追加スクリプト")
    print("=" * 60)

    # Notionトークンチェック
    if not NOTION_TOKEN:
        print("エラー: NOTION_TOKEN_TASK が設定されていません")
        sys.exit(1)

    # 日本時間で今日の日付を表示
    jst = ZoneInfo('Asia/Tokyo')
    now = datetime.now(jst)
    print(f"\n実行日時: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"検索範囲: 明日から2ヶ月先まで")

    # 御霊鎮めイベント取得
    print("\n[1] 御霊鎮めイベントを確認中...")
    events = get_upcoming_mitama_events()

    if not events:
        print("  ℹ️  対象期間に御霊鎮めはありません。")
        return

    print(f"  ✓ {len(events)}件の御霊鎮めイベントがあります")
    for event in events:
        print(f"     - {event['summary']} ({event['start'].strftime('%Y-%m-%d %H:%M')})")

    # 各イベントに対してタスク追加
    print("\n[2] タスクを追加中...")
    total_added = 0

    for event in events:
        added = add_tasks_for_event(event['start'], event['summary'])
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
            f'display notification "御霊鎮めタスク{total_added}件を追加しました" with title "御霊鎮めタスク自動追加"'
        ])


if __name__ == '__main__':
    main()
