#!/usr/bin/env python3
"""
大阪関西万博フォーラムのリアクション監視Bot

📅 リアクションが付いた投稿を解析してイベント情報を抽出し、
Googleカレンダーに自動登録する

フォーラムチャンネルID: 1439846883504689193
"""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import json
import subprocess
from datetime import datetime
import re

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🎡｜大阪関西万博 フォーラムチャンネルID（IZUMOサーバー）
EXPO_FORUM_ID = 1439846883504689193

# 処理済みリアクション記録ファイル
PROCESSED_FILE = '/Users/minamitakeshi/discord-mcp-server/expo_calendar_processed.json'

# Bot初期化
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)


def load_processed():
    """処理済みメッセージIDリストを読み込む"""
    if not os.path.exists(PROCESSED_FILE):
        return []

    try:
        with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_processed(message_id):
    """処理済みメッセージIDを保存"""
    processed = load_processed()

    if message_id not in processed:
        processed.append(message_id)

    # 最新1000件のみ保持
    processed = processed[-1000:]

    with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)


async def fetch_article_content(url):
    """URLから記事内容を取得"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    return None
    except Exception as e:
        print(f'記事取得エラー: {e}')
        return None


async def extract_event_info_with_gemini(url, article_title):
    """Gemini APIで記事からイベント情報を抽出"""

    # Gemini APIリクエスト
    gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}'

    prompt = f"""以下のURL先の記事を解析して、イベント情報があれば抽出してください。

URL: {url}
記事タイトル: {article_title}

イベント情報がある場合、以下のJSON形式で返してください：
{{
  "has_event": true,
  "event_name": "イベント名",
  "start_date": "2025-12-31",
  "start_time": "10:00",
  "end_date": "2025-12-31",
  "end_time": "17:00",
  "location": "場所",
  "description": "イベントの詳細"
}}

イベント情報がない場合：
{{
  "has_event": false
}}

注意事項：
- 日時情報が不明確な場合や過去のイベントの場合は has_event: false
- start_time/end_time が不明な場合は "00:00" を設定
- 2025年以降の未来のイベントのみ has_event: true
- JSON以外の説明文は不要
"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                gemini_url,
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    text = result['candidates'][0]['content']['parts'][0]['text']

                    # JSONを抽出（```json ブロックがある場合）
                    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
                    if json_match:
                        text = json_match.group(1)

                    event_info = json.loads(text)
                    return event_info
                else:
                    print(f'Gemini APIエラー: {response.status}')
                    return {"has_event": false}
    except Exception as e:
        print(f'イベント情報抽出エラー: {e}')
        return {"has_event": false}


def create_google_calendar_event(event_info, article_url):
    """Googleカレンダーにイベントを登録"""

    # 日時フォーマット作成
    start_datetime = f"{event_info['start_date']}T{event_info['start_time']}:00"
    end_datetime = f"{event_info['end_date']}T{event_info['end_time']}:00"

    # MCP Google Calendar APIを使用
    # Claude Code経由で実行するため、ここではシェルコマンドで呼び出し
    # 実際にはClaude CodeのMCP機能を使う必要があるため、
    # 一旦イベント情報をファイルに保存して、別プロセスで処理

    event_data = {
        "calendarId": "primary",
        "summary": event_info['event_name'],
        "start": start_datetime,
        "end": end_datetime,
        "location": event_info.get('location', ''),
        "description": f"{event_info.get('description', '')}\n\nソース: {article_url}",
        "timeZone": "Asia/Tokyo"
    }

    # イベント情報を一時ファイルに保存
    pending_file = '/Users/minamitakeshi/discord-mcp-server/expo_calendar_pending.json'

    pending_events = []
    if os.path.exists(pending_file):
        with open(pending_file, 'r', encoding='utf-8') as f:
            try:
                pending_events = json.load(f)
            except:
                pending_events = []

    pending_events.append(event_data)

    with open(pending_file, 'w', encoding='utf-8') as f:
        json.dump(pending_events, f, ensure_ascii=False, indent=2)

    print(f'✅ カレンダー登録待ちリストに追加: {event_info["event_name"]}')
    return True


@bot.event
async def on_ready():
    """Bot起動時に実行"""
    print(f'Bot起動: {bot.user}')
    print(f'監視中: 大阪関西万博フォーラム（📅 リアクションでカレンダー登録）')


@bot.event
async def on_raw_reaction_add(payload):
    """リアクション追加時に実行"""

    # 万博フォーラム以外は無視
    if payload.channel_id != EXPO_FORUM_ID:
        return

    # 📅 絵文字以外は無視
    if str(payload.emoji) != '📅':
        return

    # 処理済みチェック
    processed = load_processed()
    if payload.message_id in processed:
        print(f'⏭️  処理済み: メッセージID {payload.message_id}')
        return

    print(f'📅 リアクション検知: メッセージID {payload.message_id}')

    try:
        # チャンネルとメッセージを取得
        channel = bot.get_channel(payload.channel_id)
        if not channel:
            return

        # スレッドの場合、最初のメッセージを取得
        if isinstance(channel, discord.Thread):
            # スレッドの最初のメッセージ（starter message）を取得
            message = await channel.fetch_message(channel.id)
        else:
            message = await channel.fetch_message(payload.message_id)

        print(f'メッセージ取得: {message.content[:100]}...')

        # URLを抽出
        urls = re.findall(r'https?://[^\s]+', message.content)

        if not urls:
            print('❌ URLが見つかりません')
            return

        article_url = urls[0]
        print(f'URL: {article_url}')

        # 記事タイトルを取得（スレッドタイトルまたはメッセージの最初の行）
        if isinstance(channel, discord.Thread):
            article_title = channel.name
        else:
            article_title = message.content.split('\n')[0][:100]

        print(f'記事タイトル: {article_title}')

        # Geminiでイベント情報を抽出
        print('Gemini APIでイベント情報を抽出中...')
        event_info = await extract_event_info_with_gemini(article_url, article_title)

        if not event_info.get('has_event'):
            print('ℹ️  イベント情報が見つかりませんでした')
            # リアクションを削除
            await message.remove_reaction('📅', payload.member)
            # ❌リアクションを追加
            await message.add_reaction('❌')
            return

        print(f'✅ イベント検出: {event_info["event_name"]}')
        print(f'   日時: {event_info["start_date"]} {event_info["start_time"]}')

        # Googleカレンダーに登録
        success = create_google_calendar_event(event_info, article_url)

        if success:
            # ✅リアクションを追加
            await message.add_reaction('✅')

            # macOS通知
            os.system(f'osascript -e \'display notification "{event_info["event_name"]} をカレンダー登録待ちリストに追加しました" with title "万博カレンダー"\'')

        # 処理済みとして記録
        save_processed(payload.message_id)

    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
