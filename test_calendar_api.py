#!/usr/bin/env python3
"""
Google Calendar API テストスクリプト

サービスアカウント認証でカレンダーにテストイベントを登録
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# 設定
SERVICE_ACCOUNT_FILE = '/Users/minamitakeshi/discord-mcp-server/google-calendar-service-account.json'
KANSAI_EVENT_CALENDAR_ID = 'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com'

def test_calendar_api():
    """テストイベントをカレンダーに登録"""

    print('Google Calendar API テスト開始...')

    try:
        # サービスアカウント認証
        print('1. サービスアカウント認証中...')
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        print('   ✅ 認証成功')

        # Calendar APIクライアント作成
        print('2. Calendar APIクライアント作成中...')
        service = build('calendar', 'v3', credentials=credentials)
        print('   ✅ クライアント作成成功')

        # テストイベントデータ
        tomorrow = datetime.now() + timedelta(days=1)
        start_datetime = tomorrow.replace(hour=10, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S')
        end_datetime = tomorrow.replace(hour=11, minute=0, second=0).strftime('%Y-%m-%dT%H:%M:%S')

        event = {
            'summary': '【テスト】大阪関西万博カレンダー連携テスト',
            'location': '大阪',
            'description': 'Discord Botからの自動登録テスト\n\nこのイベントは削除してOKです。',
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'Asia/Tokyo',
            },
        }

        print('3. テストイベント登録中...')
        print(f'   イベント名: {event["summary"]}')
        print(f'   日時: {start_datetime}')

        # カレンダーにイベント登録
        event_result = service.events().insert(
            calendarId=KANSAI_EVENT_CALENDAR_ID,
            body=event
        ).execute()

        print('   ✅ イベント登録成功！')
        print(f'   イベントID: {event_result.get("id")}')
        print(f'   イベントURL: {event_result.get("htmlLink")}')
        print('')
        print('✅ 全てのテストが成功しました！')
        print('Googleカレンダーで「関西イベント情報」を確認してください。')

        return True

    except Exception as e:
        print(f'❌ エラー発生: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_calendar_api()
