import sys
sys.path.insert(0, '/Users/minamitakeshi/discord-mcp-server')
from daily_schedule_post import get_today_events, format_schedule_message

events = get_today_events()
print(f"取得したイベント数: {len(events)}")
for i, event in enumerate(events):
    print(f"\nイベント {i+1}:")
    print(f"  タイトル: {event['title']}")
    print(f"  カレンダー: {event['calendar_name']}")
    print(f"  開始: {event['start']}")
    print(f"  終了: {event['end']}")

print("\n" + "="*50)
print("フォーマット後のメッセージ:")
print("="*50)
message = format_schedule_message(events)
print(message)
