#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai

load_dotenv()

# Discord Bot Token
TOKEN = os.getenv('DISCORD_TOKEN')

# Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# 監視対象チャンネルID
OCR_CHANNEL_IDS = [
    1435548125207986198,  # Minamiサーバー：📄｜カレンダー画像登録
    1435629460102582292,  # IZUMOサーバー：📄｜カレンダー画像登録
]

# Google Calendar API設定
CREDENTIALS_FILE = os.path.expanduser('~/shared-google-calendar/credentials.json')
TOKEN_FILE = os.path.expanduser('~/.config/google-calendar-mcp/tokens.json')
CALENDAR_ID = 'primary'

# Gemini API使用量トラッキング
USAGE_LOG_FILE = os.path.expanduser('~/discord-mcp-server/gemini_usage.json')
DAILY_REQUEST_LIMIT = 250  # Gemini Flash無料枠
WARNING_THRESHOLD = 200    # 警告を出す閾値（80%）

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# セッションストレージ
ocr_sessions = {}

def log(level, message):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    print(f'[OCR Bot][{level}] {timestamp} - {message}')

    log_file = os.path.expanduser('~/discord-mcp-server/ocr_calendar_bot.log')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'[OCR Bot][{level}] {timestamp} - {message}\n')

def get_usage_stats():
    """Gemini API使用量を取得"""
    today = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists(USAGE_LOG_FILE):
        return {'date': today, 'count': 0}

    try:
        with open(USAGE_LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 日付が変わっていたらリセット
        if data.get('date') != today:
            return {'date': today, 'count': 0}

        return data
    except Exception as e:
        log('ERROR', f'使用量ログ読み込みエラー: {e}')
        return {'date': today, 'count': 0}

def increment_usage():
    """Gemini API使用量をインクリメント"""
    stats = get_usage_stats()
    stats['count'] += 1

    try:
        with open(USAGE_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        log('INFO', f'Gemini API使用量: {stats["count"]}/{DAILY_REQUEST_LIMIT} (日付: {stats["date"]})')

        # 警告チェック
        if stats['count'] >= DAILY_REQUEST_LIMIT:
            log('ERROR', f'⚠️ 本日のGemini API無料枠を使い切りました！これ以上リクエストできません。')
            return False
        elif stats['count'] >= WARNING_THRESHOLD:
            log('WARNING', f'⚠️ Gemini API使用量が警告閾値を超えました: {stats["count"]}/{DAILY_REQUEST_LIMIT}')

        return True
    except Exception as e:
        log('ERROR', f'使用量ログ書き込みエラー: {e}')
        return True  # エラー時は続行を許可（安全側に倒す）

def check_usage_limit():
    """Gemini API使用量の上限チェック"""
    stats = get_usage_stats()

    if stats['count'] >= DAILY_REQUEST_LIMIT:
        log('ERROR', f'本日のGemini API無料枠を使い切りました: {stats["count"]}/{DAILY_REQUEST_LIMIT}')
        return False

    return True

def get_calendar_service():
    """Google Calendar APIサービスを取得"""
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)

    if 'normal' in token_data:
        token_data = token_data['normal']

    with open(CREDENTIALS_FILE, 'r') as f:
        credentials_data = json.load(f)
        client_id = credentials_data['installed']['client_id']
        client_secret = credentials_data['installed']['client_secret']

    creds = Credentials(
        token=token_data['access_token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
    )

    return build('calendar', 'v3', credentials=creds)

async def create_calendar_event(event_data):
    """Googleカレンダーにイベントを登録"""
    try:
        service = get_calendar_service()

        event = {
            'summary': event_data['title'],
            'location': event_data.get('location', ''),
            'description': event_data.get('description', ''),
        }

        if event_data.get('start'):
            if 'T' in event_data['start']:
                event['start'] = {'dateTime': event_data['start'], 'timeZone': 'Asia/Tokyo'}
                event['end'] = {'dateTime': event_data['end'], 'timeZone': 'Asia/Tokyo'}
            else:
                event['start'] = {'date': event_data['start']}
                event['end'] = {'date': event_data['end']}
        else:
            raise Exception('日時が指定されていません')

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

        log('SUCCESS', f'カレンダー登録完了: {created_event.get("htmlLink")}')
        return created_event

    except Exception as e:
        log('ERROR', f'カレンダー登録エラー: {e}')
        raise

async def analyze_image_with_gemini(image_url):
    """Gemini APIで画像を解析してイベント情報を抽出"""
    try:
        # 使用量チェック
        if not check_usage_limit():
            raise Exception('本日のGemini API無料枠（250リクエスト/日）を使い切りました。明日まで待ってください。')

        log('INFO', f'Gemini API解析開始: {image_url}')

        # 画像をダウンロード
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise Exception(f'画像ダウンロード失敗: {response.status}')
                image_data = await response.read()

        log('INFO', f'画像ダウンロード完了: {len(image_data)} bytes')

        # Gemini モデル初期化
        model = genai.GenerativeModel('gemini-1.5-flash')

        # プロンプト作成
        prompt = """この画像からイベント情報を抽出してください。

以下のJSON形式で返してください：
{
  "title": "イベントのタイトル",
  "dates": ["YYYY-MM-DD", "YYYY-MM-DD", ...],
  "time": "HH:MM形式の時刻（不明な場合はnull）",
  "location": "場所（不明な場合は空文字列）",
  "description": "イベントの説明や補足情報"
}

注意：
- 日付は必ず YYYY-MM-DD 形式の配列で返してください（例: ["2025-11-22", "2025-11-23"]）
- 年が省略されている場合は、現在の年（2025年）を使用してください
- 複数の日付がある場合は、全ての日付を "dates" 配列に含めてください
- 日付が1つだけの場合も配列形式で返してください（例: ["2025-11-22"]）
- 時刻は HH:MM 形式で返してください（例: 14:30）
- 時刻が不明な場合は null を返してください
- 場所が不明な場合は空文字列を返してください
- 日付が全く検出できない場合は空配列 [] を返してください
- JSON以外の文字列は含めないでください"""

        # 画像を解析
        image_part = {
            'mime_type': 'image/jpeg',
            'data': image_data
        }

        log('INFO', 'Gemini APIリクエスト送信中...')
        response = model.generate_content([prompt, image_part])

        # 使用量をインクリメント
        increment_usage()

        log('INFO', f'Gemini API応答受信: {response.text[:200]}...')

        # JSONをパース
        response_text = response.text.strip()
        # コードブロックを除去
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        event_info = json.loads(response_text)

        log('SUCCESS', f'Gemini解析成功: {event_info}')
        return event_info

    except Exception as e:
        log('ERROR', f'Gemini解析エラー: {e}')
        raise

@client.event
async def on_ready():
    log('INFO', f'Bot起動: {client.user}')
    log('INFO', f'OCRチャンネル監視開始: {OCR_CHANNEL_IDS}')

    # 現在の使用量を表示
    stats = get_usage_stats()
    log('INFO', f'本日のGemini API使用量: {stats["count"]}/{DAILY_REQUEST_LIMIT} (残り: {DAILY_REQUEST_LIMIT - stats["count"]})')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id not in OCR_CHANNEL_IDS:
        return

    if not message.attachments:
        return

    log('INFO', f'画像受信 | {{"author": "{message.author.name}", "attachments": {len(message.attachments)}}}')

    processing_msg = await message.channel.send('📷 Gemini APIで画像解析中...')

    try:
        for attachment in message.attachments:
            if not attachment.content_type or not attachment.content_type.startswith('image/'):
                continue

            session_id = str(attachment.id)
            image_url = attachment.url

            log('INFO', f'画像解析開始: {image_url}')

            # Gemini APIで画像を解析
            try:
                event_info = await analyze_image_with_gemini(image_url)
            except Exception as e:
                error_msg = str(e)
                if '無料枠' in error_msg:
                    await processing_msg.edit(content=f'⚠️ {error_msg}')
                else:
                    await processing_msg.edit(content=f'⚠️ エラー: {error_msg}')
                continue

            if not event_info:
                await processing_msg.edit(content='⚠️ 画像からイベント情報を抽出できませんでした。')
                continue

            ocr_sessions[session_id] = {
                'event_info': event_info,
                'user_id': message.author.id
            }

            dates = event_info.get('dates', [])
            dates_str = ', '.join(dates) if dates else '(未検出)'

            # 使用量を取得
            stats = get_usage_stats()
            usage_info = f"📊 Gemini API使用量: {stats['count']}/{DAILY_REQUEST_LIMIT} (残り: {DAILY_REQUEST_LIMIT - stats['count']})"

            analysis_message = f"""🤖 **Gemini AI解析結果**

**タイトル**: {event_info.get('title') or '(未検出)'}
**日付**: {dates_str} ({len(dates)}件)
**時刻**: {event_info.get('time') or '(終日)'}
**場所**: {event_info.get('location') or '(未検出)'}

{usage_info}

このままカレンダーに登録しますか？（{len(dates)}件のイベントを作成します）"""

            view = discord.ui.View(timeout=300)

            register_button = discord.ui.Button(
                label="✅ カレンダーに登録",
                style=discord.ButtonStyle.success,
                custom_id=f"register_{session_id}"
            )

            cancel_button = discord.ui.Button(
                label="❌ キャンセル",
                style=discord.ButtonStyle.secondary,
                custom_id=f"cancel_{session_id}"
            )

            async def register_callback(interaction):
                if interaction.user.id != ocr_sessions.get(session_id, {}).get('user_id'):
                    await interaction.response.send_message("⚠️ この操作はイベントを作成したユーザーのみ実行できます", ephemeral=True)
                    return

                await interaction.response.defer()

                session_data = ocr_sessions.get(session_id)
                if not session_data:
                    await interaction.followup.send("⚠️ セッションが見つかりません", ephemeral=True)
                    return

                event_info = session_data.get('event_info')
                if not event_info:
                    await interaction.followup.send("⚠️ イベント情報が見つかりません", ephemeral=True)
                    return

                dates = event_info.get('dates', [])
                if not dates:
                    await interaction.followup.send("⚠️ 日付が検出されませんでした。カレンダー登録できません。", ephemeral=True)
                    return

                if not event_info.get('title'):
                    await interaction.followup.send("⚠️ タイトルが検出されませんでした。カレンダー登録できません。", ephemeral=True)
                    return

                # 複数日付に対してそれぞれカレンダーイベントを作成
                created_events = []
                failed_dates = []

                for date in dates:
                    try:
                        # 日時の整形
                        start_datetime = None
                        end_datetime = None

                        if event_info.get('time'):
                            start_datetime = f"{date}T{event_info['time']}:00"
                            hour, minute = event_info['time'].split(':')
                            end_hour = (int(hour) + 1) % 24
                            end_datetime = f"{date}T{end_hour:02d}:{minute}:00"
                        else:
                            start_datetime = date
                            end_datetime = date

                        calendar_data = {
                            'title': event_info['title'],
                            'start': start_datetime,
                            'end': end_datetime,
                            'location': event_info.get('location', ''),
                            'description': event_info.get('description', ''),
                        }

                        created_event = await create_calendar_event(calendar_data)
                        created_events.append(date)

                    except Exception as e:
                        log('ERROR', f'カレンダー登録エラー ({date}): {e}')
                        failed_dates.append(date)

                # 結果メッセージ作成
                if created_events:
                    dates_str = ', '.join(created_events)

                    # 使用量を取得
                    stats = get_usage_stats()
                    usage_info = f"\n\n📊 Gemini API使用量: {stats['count']}/{DAILY_REQUEST_LIMIT} (残り: {DAILY_REQUEST_LIMIT - stats['count']})"

                    final_message = f"""✅ **カレンダー登録完了**

**タイトル**: {event_info['title']}
**登録日付**: {dates_str} ({len(created_events)}件)
**時刻**: {event_info.get('time') or '(終日)'}
**場所**: {event_info.get('location') or '未設定'}{usage_info}"""

                    if failed_dates:
                        failed_str = ', '.join(failed_dates)
                        final_message += f"\n\n⚠️ 登録失敗: {failed_str}"

                    await interaction.edit_original_response(content=final_message, view=None)
                else:
                    await interaction.followup.send("⚠️ 全ての日付でカレンダー登録に失敗しました", ephemeral=True)

                if session_id in ocr_sessions:
                    del ocr_sessions[session_id]

            async def cancel_callback(interaction):
                await interaction.response.edit_message(content="❌ キャンセルしました", view=None)
                if session_id in ocr_sessions:
                    del ocr_sessions[session_id]

            register_button.callback = register_callback
            cancel_button.callback = cancel_callback
            view.add_item(register_button)
            view.add_item(cancel_button)

            await processing_msg.edit(content=analysis_message, view=view)

    except Exception as e:
        log('ERROR', f'メッセージ処理エラー: {e}')
        await processing_msg.edit(content=f'⚠️ エラーが発生しました: {str(e)}')

if __name__ == '__main__':
    log('INFO', 'OCR→カレンダー登録Bot起動中（Gemini API連携モード）...')
    client.run(TOKEN)
