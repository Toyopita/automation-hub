#!/usr/bin/env python3
"""
毎朝6時にGoogleカレンダーとNotionタスクをDiscordに投稿するスクリプト
GASの「タスク通知GAS」の機能をDiscord版に移植
"""

import os
import discord
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import sys
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle

# 環境変数読み込み
load_dotenv()

# 設定
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1434368052916392076  # 📅｜今日の予定チャンネル
DEADLINE_DAYS = 7  # 締切日数
NOTION_TOKEN = os.getenv('NOTION_TOKEN')  # .envに追加が必要

# カレンダーIDの設定（GASと同じ順序）
CALENDAR_CONFIGS = [
    {'name': '六曜カレンダー', 'id': 'br7nsak3pjv3d379ddrf4bfgpo7splo1@import.calendar.google.com', 'today_only': True},
    {'name': '祖霊社', 'id': 'cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com', 'today_only': False, 'group': '神社'},
    {'name': '本社', 'id': '079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com', 'today_only': False, 'group': '神社'},
    {'name': '年祭', 'id': '40ea48b73cb27b73af8113fc8d9943a609f1a75e47eb65dd5a126fea516004ea@group.calendar.google.com', 'today_only': False, 'group': '神社'},
    {'name': '冥福祭', 'id': '4985421b6573a758fa7cc5c3c610ee1f725ef2e2e29fa8a758690043dc02c6c5@group.calendar.google.com', 'today_only': False, 'group': '神社'},
    {'name': 'プライベート', 'id': 'izumooyashiro.osaka.takeshi@gmail.com', 'today_only': False},
    {'name': '関西イベント情報', 'id': 'ba311ba9532e646a2b72cb8ae66eae3fe2a364b44fcfbf34f7b0f9dbc297b0f0@group.calendar.google.com', 'today_only': False}
]

# NotionタスクDB ID
NOTION_TASK_DB_ID = '1c800160-1818-807c-b083-f475eb3a07b9'
NOTION_PROJECT_DB_ID = '1c800160-1818-8004-9609-c1250a7e3478'


def format_japanese_date(date_obj):
    """日付を和式フォーマットに変換: 2025年11月2日（土）"""
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[date_obj.weekday()]
    return f"{date_obj.year}年{date_obj.month}月{date_obj.day}日（{weekday}）"


def format_time(dt):
    """時刻をHH:MM形式に変換"""
    return dt.strftime('%H:%M')


async def fetch_calendar_events_mcp():
    """
    Google Calendar MCPを使ってカレンダー予定を取得

    Note: この関数はMCP経由で呼び出す必要があります
    実際の実装ではClaude Code経由でMCPツールを呼び出します
    """
    # TODO: MCP経由でGoogle Calendarから予定を取得
    # 今はプレースホルダーとして空リストを返す
    print("⚠️ Google Calendar MCPの統合が必要です")
    return []


async def fetch_notion_tasks_mcp():
    """
    Notion MCPを使ってタスクを取得

    Note: この関数はMCP経由で呼び出す必要があります
    実際の実装ではClaude Code経由でMCPツールを呼び出します
    """
    # TODO: MCP経由でNotionタスクを取得
    print("⚠️ Notion MCPの統合が必要です")
    return []


def build_discord_message(events, tasks):
    """
    Discordメッセージを作成（マークダウン形式）
    GASのHTMLメールフォーマットをDiscord用に変換
    """
    today = datetime.now()
    today_str = format_japanese_date(today)

    # メッセージのヘッダー
    message = f"""# 📅 今週の予定・締切タスク統合通知

**{today_str} から1週間の予定とタスク状況**

"""

    # カレンダー予定セクション（GASと同じセクション分け）
    calendar_sections = [
        {
            'title': '六曜カレンダー',
            'emoji': '🗓️',
            'calendar_names': ['六曜カレンダー'],
            'today_only': True
        },
        {
            'title': '神社（祖霊社・本社・年祭・冥福祭）',
            'emoji': '⛩️',
            'calendar_names': ['祖霊社', '本社', '年祭', '冥福祭'],
            'today_only': False
        },
        {
            'title': 'プライベート',
            'emoji': '🏠',
            'calendar_names': ['プライベート'],
            'today_only': False
        },
        {
            'title': '関西イベント情報',
            'emoji': '🎪',
            'calendar_names': ['関西イベント情報'],
            'today_only': False
        }
    ]

    for section in calendar_sections:
        section_events = [
            e for e in events
            if e.get('calendar_name') in section['calendar_names']
        ]

        # 六曜カレンダーは今日のみ
        if section['today_only']:
            section_events = [
                e for e in section_events
                if e.get('start_date', '').startswith(today.strftime('%Y-%m-%d'))
            ]

        if not section_events:
            continue

        message += f"\n## {section['emoji']} {section['title']}\n\n"

        for event in section_events:
            title = event.get('title', '（タイトルなし）')
            start_date = event.get('start_date', '')
            is_all_day = event.get('is_all_day', False)
            location = event.get('location', '')

            if is_all_day:
                time_str = f"{start_date} **終日**"
            else:
                start_time = event.get('start_time', '')
                end_time = event.get('end_time', '')
                time_str = f"{start_date} {start_time}～{end_time}"

            message += f"- **{title}**\n"
            message += f"  ⏰ {time_str}\n"
            if location:
                message += f"  📍 {location}\n"
            message += "\n"

    # Notionタスクセクション
    if tasks:
        message += f"\n## 🚨 締切間近タスク（未了） - {len(tasks)}件\n\n"

        for task in tasks:
            task_name = task.get('task_name', '（タイトルなし）')
            due_date = task.get('due_date', '')
            project_name = task.get('project_name', 'プロジェクト未設定')
            is_overdue = task.get('is_overdue', False)

            if is_overdue:
                message += f"- 🔴 **{task_name}** 【期限超過】\n"
            else:
                message += f"- **{task_name}**\n"

            message += f"  📂 {project_name}\n"
            message += f"  ⏰ {due_date}\n\n"
    else:
        message += "\n## ✅ 締切間近の未了タスクはありません\n\n"

    # フッター
    message += f"\n---\n💡 **このメッセージは自動送信されています**\n"
    message += f"送信日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n"

    return message


async def post_to_discord(message):
    """Discordにメッセージを投稿"""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')

        channel = client.get_channel(CHANNEL_ID)
        if channel:
            # メッセージが2000文字を超える場合は分割
            if len(message) <= 2000:
                await channel.send(message)
            else:
                # 2000文字ごとに分割して送信
                chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
                for chunk in chunks:
                    await channel.send(chunk)
                    await asyncio.sleep(1)  # レート制限対策

            print(f'✅ メッセージを投稿しました: #{channel.name}')
        else:
            print(f'❌ チャンネルが見つかりません: {CHANNEL_ID}')

        await client.close()

    await client.start(DISCORD_TOKEN)


async def main():
    """メイン処理"""
    print("=== 今日の予定・タスク通知 開始 ===")
    print(f"実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

    # カレンダー予定とタスクを取得（MCP経由）
    # ⚠️ 注意: この部分はClaude Code経由でMCPを呼び出す必要があります
    # 現在はプレースホルダーとして空リストを使用
    print("\n📅 カレンダー予定を取得中...")
    events = await fetch_calendar_events_mcp()
    print(f"取得した予定数: {len(events)}")

    print("\n📋 Notionタスクを取得中...")
    tasks = await fetch_notion_tasks_mcp()
    print(f"取得したタスク数: {len(tasks)}")

    # Discordメッセージを作成
    print("\n💬 Discordメッセージを作成中...")
    message = build_discord_message(events, tasks)

    # Discordに投稿
    print("\n📤 Discordに投稿中...")
    await post_to_discord(message)

    print("\n=== 処理完了 ===")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n中断されました")
        sys.exit(0)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
