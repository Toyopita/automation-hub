import sys
sys.path.insert(0, '/Users/minamitakeshi/discord-mcp-server')
from daily_schedule_post import get_calendar_service, CALENDAR_IDS, CALENDAR_NAMES
from datetime import datetime, timedelta

service = get_calendar_service()

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
tomorrow = today + timedelta(days=1)

time_min = today.isoformat() + 'Z'
time_max = tomorrow.isoformat() + 'Z'

print(f"検索範囲: {time_min} ~ {time_max}\n")

for calendar_id in CALENDAR_IDS:
    calendar_name = CALENDAR_NAMES.get(calendar_id, calendar_id)
    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        print(f"✅ {calendar_name}: {len(events)}件")
        for event in events:
            print(f"   - {event.get('summary', '（タイトルなし）')}")
    except Exception as e:
        print(f"❌ {calendar_name}: エラー - {e}")
    print()
