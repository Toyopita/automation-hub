#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冥福祭タスク自動追加スクリプト

Googleカレンダー「冥福祭」から未来のイベントを取得し、
その前日を期限として12タスクをNotionに自動追加する。
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 環境変数から取得
NOTION_TOKEN = os.environ.get('NOTION_TOKEN_TASK')
MEIFUKU_PROJECT_ID = "1ce00160-1818-80b9-8dca-c747819721f0"
TASK_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"
USER_ID = "4463c065-1795-49cf-a939-1b018b08e25b"  # Minami

# 追加するタスクリスト
TASKS = [
    "冥福祭の預り金を前日に処理する",
    "玉串仮案の整理",
    "玉串案の内容整理",
    "厚畳",
    "祝詞仮案の整理",
    "祓詞用の願い主名簿",
    "祝詞案の整理",
    "冥福祭祓詞",
    "冥福祭の読み上げ芳名簿の整理",
    "冥福祭の祝詞を唱える",
    "参列者用玉串",
    "斎主用玉串"
]


def get_meifuku_events():
    """Googleカレンダーから冥福祭イベントを取得"""
    try:
        # 日本時間で今日の日付を取得
        now = datetime.now(ZoneInfo('Asia/Tokyo'))
        today_str = now.strftime('%Y-%m-%d')

        # 1年後まで検索
        future_date = now + timedelta(days=365)
        future_str = future_date.strftime('%Y-%m-%d')

        # MCPコマンドを使ってカレンダーイベントを取得
        result = subprocess.run([
            'claude', 'mcp', 'call',
            'google-calendar',
            'list-events',
            '--args', json.dumps({
                "calendarId": "4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com",
                "timeMin": f"{today_str}T00:00:00+09:00",
                "timeMax": f"{future_str}T23:59:59+09:00",
                "timeZone": "Asia/Tokyo"
            })
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"エラー: カレンダーイベント取得失敗: {result.stderr}")
            return []

        # 出力をパース（JSONとして）
        output = result.stdout.strip()
        # MCPの出力から実際のJSONを抽出
        if "```json" in output:
            json_start = output.find("```json") + 7
            json_end = output.find("```", json_start)
            json_str = output[json_start:json_end].strip()
            events_data = json.loads(json_str)
        else:
            events_data = json.loads(output)

        events = []
        if isinstance(events_data, dict) and 'items' in events_data:
            for item in events_data['items']:
                if '冥福祭' in item.get('summary', ''):
                    # 開始日時を解析
                    start = item.get('start', {})
                    if 'dateTime' in start:
                        event_date = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                    elif 'date' in start:
                        event_date = datetime.fromisoformat(start['date'])
                    else:
                        continue

                    events.append({
                        'summary': item.get('summary'),
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
        # MCPコマンドを使ってNotionタスクを検索
        result = subprocess.run([
            'claude', 'mcp', 'call',
            'notionApi',
            'API-post-database-query',
            '--args', json.dumps({
                "database_id": TASK_DB_ID,
                "filter": {
                    "and": [
                        {
                            "property": "プロジェクト名",
                            "relation": {"contains": MEIFUKU_PROJECT_ID}
                        },
                        {
                            "property": "期限",
                            "date": {"equals": deadline}
                        }
                    ]
                }
            })
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"警告: タスク検索失敗: {result.stderr}")
            return False

        # 既存タスクがあるかチェック
        output = result.stdout.strip()
        if "```json" in output:
            json_start = output.find("```json") + 7
            json_end = output.find("```", json_start)
            json_str = output[json_start:json_end].strip()
            data = json.loads(json_str)
        else:
            data = json.loads(output)

        # resultsが空でなければ既にタスクが存在
        return len(data.get('results', [])) > 0

    except Exception as e:
        print(f"警告: タスク検索エラー: {e}")
        return False


def add_tasks_for_event(event_date, event_name):
    """指定された冥福祭の前日を期限としてタスクを追加"""
    # 前日を計算（日本時間）
    deadline = (event_date - timedelta(days=1)).strftime('%Y-%m-%d')

    # 既にタスクが存在するかチェック
    if check_existing_tasks(deadline):
        print(f"✓ {event_name} ({event_date.strftime('%Y-%m-%d')}) のタスクは既に追加済み")
        return 0

    print(f"→ {event_name} ({event_date.strftime('%Y-%m-%d')}) のタスクを追加中...")

    added_count = 0
    for task_name in TASKS:
        try:
            # MCPコマンドを使ってNotionにタスク追加
            result = subprocess.run([
                'claude', 'mcp', 'call',
                'notionApi',
                'API-post-page',
                '--args', json.dumps({
                    "parent": {"type": "database_id", "database_id": TASK_DB_ID},
                    "properties": {
                        "タスク名": {"title": [{"text": {"content": task_name}}]},
                        "プロジェクト名": {"relation": [{"id": MEIFUKU_PROJECT_ID}]},
                        "期限": {"date": {"start": deadline}},
                        "タグ": {"multi_select": [{"name": "冥福祭"}]},
                        "担当者": {"people": [{"id": USER_ID}]}
                    }
                })
            ], capture_output=True, text=True)

            if result.returncode == 0:
                added_count += 1
            else:
                print(f"  警告: {task_name} の追加に失敗: {result.stderr}")

        except Exception as e:
            print(f"  エラー: {task_name} の追加中にエラー: {e}")

    print(f"  ✓ {added_count}/{len(TASKS)} タスクを追加しました")
    return added_count


def main():
    print("=" * 60)
    print("冥福祭タスク自動追加スクリプト")
    print("=" * 60)

    # Notionトークンチェック
    if not NOTION_TOKEN:
        print("エラー: NOTION_TOKEN_TASK が設定されていません")
        sys.exit(1)

    # 冥福祭イベント取得
    print("\n[1] Googleカレンダーから冥福祭イベントを取得中...")
    events = get_meifuku_events()

    if not events:
        print("  冥福祭イベントが見つかりませんでした")
        return

    print(f"  ✓ {len(events)}件の冥福祭イベントを検出")

    # 各イベントに対してタスク追加
    print("\n[2] タスクを追加中...")
    total_added = 0

    for event in events:
        added = add_tasks_for_event(event['start'], event['summary'])
        total_added += added

    # 結果通知
    print("\n" + "=" * 60)
    print(f"完了: {total_added}件のタスクを追加しました")
    print("=" * 60)

    # macOS通知
    if total_added > 0:
        subprocess.run([
            'osascript', '-e',
            f'display notification "冥福祭タスク{total_added}件をNotionに追加しました" with title "冥福祭タスク自動追加"'
        ])


if __name__ == '__main__':
    main()
