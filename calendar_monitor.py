#!/usr/bin/env python3
"""
Discord ⇒ MacBook ⇒ Google Calendar ―― カレンダー登録Bot

Discordの「📅｜カレンダー登録」チャンネルの投稿を監視し、
予定情報を解析してGoogle Calendarに自動登録します。

カレンダー登録チャンネルID: 1434324456842727676, 1434331124359757936
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
import discord
from discord.ext import commands
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from discord_auth_handler import run_with_retry

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# 📅｜カレンダー登録 チャンネルID（複数サーバー対応）
CALENDAR_CHANNEL_IDS = [
    1434324456842727676,  # Minamiサーバー
    1434331124359757936,  # IZUMOサーバー
]

# Google Calendar API設定
TOKEN_FILE = os.path.expanduser("~/.config/google-calendar-mcp/tokens.json")
CREDENTIALS_FILE = os.path.expanduser("~/claude-calendar-setup/credentials.json")

# カレンダーIDマッピング
CALENDAR_IDS = {
    "プライベート": "izumooyashiro.osaka.takeshi@gmail.com",
    "祖霊社": "cf7eae583e48c538ae20a84a8d238f9590555ffc283752864fb2252e5ba24555@group.calendar.google.com",
    "本社": "079e3c154e7e09e8bf9844a7d6244981c48f5282252f8ec346286e66018025bb@group.calendar.google.com",
}

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 処理済みメッセージIDを記録（重複防止）
processed_messages = set()

# Google Calendar API クライアント
calendar_service = None


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[カレンダー][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg, flush=True)


def init_google_calendar():
    """Google Calendar APIの初期化"""
    global calendar_service
    try:
        # トークンファイルから認証情報を読み込み
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)

        # "normal"キーの下にトークン情報がある
        if 'normal' in token_data:
            token_data = token_data['normal']

        # credentials.jsonからclient_idとclient_secretを読み込み
        with open(CREDENTIALS_FILE, 'r') as f:
            creds_data = json.load(f)
            client_id = creds_data['installed']['client_id']
            client_secret = creds_data['installed']['client_secret']

        creds = Credentials(
            token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=[token_data.get('scope', 'https://www.googleapis.com/auth/calendar')]
        )

        calendar_service = build('calendar', 'v3', credentials=creds)
        log('INFO', 'Google Calendar API初期化完了')
        return True

    except Exception as e:
        log('ERROR', 'Google Calendar API初期化エラー', {'error': str(e)})
        return False


def parse_calendar_message(text: str) -> Optional[Dict]:
    """
    カレンダー登録メッセージを解析

    対応フォーマット:
    - 11/5 10:00 散髪
    - 11月5日 10時30分 祖霊社会議
    - 2025-11-05 9:00-11:00 出社
    - 11/10 午後2時から4時 ミーティング
    - 11/5 10:00 散髪 @プライベート (カレンダー指定も可能)

    Returns:
        {'date': '2025-11-05', 'start_time': '10:00', 'end_time': '11:00', 'summary': '散髪', 'calendar': 'プライベート' or None}
    """
    try:
        log('DEBUG', '解析開始', {'text': text})

        # 全角数字を半角に変換
        text = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # カレンダー指定を抽出（オプショナル）
        calendar_match = re.search(r'@(プライベート|祖霊社|本社)', text)
        calendar_name = calendar_match.group(1) if calendar_match else None

        # 日付解析
        current_year = datetime.now().year
        date_str = None

        # パターン1: YYYY-MM-DD
        date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
        if date_match:
            year, month, day = date_match.groups()
            date_str = f"{year}-{int(month):02d}-{int(day):02d}"

        # パターン2: YYYY年MM月DD日
        if not date_str:
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
            if date_match:
                year, month, day = date_match.groups()
                date_str = f"{year}-{int(month):02d}-{int(day):02d}"

        # パターン3: MM月DD日 (今年)
        if not date_str:
            date_match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
            if date_match:
                month, day = date_match.groups()
                date_str = f"{current_year}-{int(month):02d}-{int(day):02d}"

        # パターン4: MM/DD (今年)
        if not date_str:
            date_match = re.search(r'(\d{1,2})/(\d{1,2})', text)
            if date_match:
                month, day = date_match.groups()
                date_str = f"{current_year}-{int(month):02d}-{int(day):02d}"

        if not date_str:
            log('WARN', '日付が見つかりません', {'text': text})
            return None

        # 時刻解析
        start_time = None
        end_time = None

        # 午前/午後の変換用
        def convert_ampm(hour_str, is_pm):
            hour = int(hour_str)
            if is_pm and hour < 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
            return hour

        # パターン1: HH:MM-HH:MM
        time_match = re.search(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', text)
        if time_match:
            start_hour, start_min, end_hour, end_min = time_match.groups()
            start_time = f"{int(start_hour):02d}:{start_min}"
            end_time = f"{int(end_hour):02d}:{end_min}"

        # パターン2: HH時MM分-HH時MM分
        if not start_time:
            time_match = re.search(r'(\d{1,2})時(\d{1,2})分[^0-9]*(\d{1,2})時(\d{1,2})分', text)
            if time_match:
                start_hour, start_min, end_hour, end_min = time_match.groups()
                start_time = f"{int(start_hour):02d}:{int(start_min):02d}"
                end_time = f"{int(end_hour):02d}:{int(end_min):02d}"

        # パターン3: 午前/午後HH時MM分から午前/午後HH時MM分
        if not start_time:
            time_match = re.search(r'(午前|午後)(\d{1,2})時(\d{1,2})分[^0-9]*(午前|午後)(\d{1,2})時(\d{1,2})分', text)
            if time_match:
                start_ampm, start_hour, start_min, end_ampm, end_hour, end_min = time_match.groups()
                start_h = convert_ampm(start_hour, start_ampm == '午後')
                end_h = convert_ampm(end_hour, end_ampm == '午後')
                start_time = f"{start_h:02d}:{int(start_min):02d}"
                end_time = f"{end_h:02d}:{int(end_min):02d}"

        # パターン4: HH時MM分 (終了時刻なし、1時間後に設定)
        if not start_time:
            time_match = re.search(r'(\d{1,2})時(\d{1,2})分', text)
            if time_match:
                start_hour, start_min = time_match.groups()
                start_time = f"{int(start_hour):02d}:{int(start_min):02d}"
                # 1時間後を終了時刻に
                end_h = (int(start_hour) + 1) % 24
                end_time = f"{end_h:02d}:{int(start_min):02d}"

        # パターン5: HH:MM (終了時刻なし、1時間後に設定)
        if not start_time:
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                start_hour, start_min = time_match.groups()
                start_time = f"{int(start_hour):02d}:{start_min}"
                # 1時間後を終了時刻に
                end_h = (int(start_hour) + 1) % 24
                end_time = f"{end_h:02d}:{start_min}"

        # パターン6: 午前/午後HH時 (分なし、1時間後に設定)
        if not start_time:
            time_match = re.search(r'(午前|午後)(\d{1,2})時', text)
            if time_match:
                ampm, start_hour = time_match.groups()
                start_h = convert_ampm(start_hour, ampm == '午後')
                start_time = f"{start_h:02d}:00"
                end_h = (start_h + 1) % 24
                end_time = f"{end_h:02d}:00"

        # パターン7: HH時 (分なし、1時間後に設定)
        if not start_time:
            time_match = re.search(r'(\d{1,2})時', text)
            if time_match:
                start_hour = time_match.group(1)
                start_time = f"{int(start_hour):02d}:00"
                end_h = (int(start_hour) + 1) % 24
                end_time = f"{end_h:02d}:00"

        # 時刻なしの場合は終日イベント
        is_all_day = start_time is None

        # イベント名を抽出（日付・時刻・カレンダー指定を除いた部分）
        summary = text
        # 日付部分を削除
        summary = re.sub(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}日?', '', summary)
        summary = re.sub(r'\d{1,2}[月/]\d{1,2}日?', '', summary)
        # 時刻部分を削除
        summary = re.sub(r'(午前|午後)?\d{1,2}[時:]\d{0,2}分?[-〜から]?(午前|午後)?\d{0,2}[時:]?\d{0,2}分?', '', summary)
        # カレンダー指定を削除
        summary = re.sub(r'@(プライベート|祖霊社|本社)', '', summary)
        # 余分なスペースを削除
        summary = summary.strip()

        if not summary:
            summary = "（タイトルなし）"

        result = {
            'date': date_str,
            'start_time': start_time,
            'end_time': end_time,
            'summary': summary,
            'calendar': calendar_name,  # Noneの場合はボタン選択
            'is_all_day': is_all_day
        }

        log('DEBUG', '解析結果', result)
        return result

    except Exception as err:
        log('ERROR', 'parse_calendar_message例外', {'error': str(err)})
        return None


async def create_calendar_event(data: Dict) -> bool:
    """
    Google Calendarに予定を登録

    Args:
        data: 解析済みデータ

    Returns:
        成功: True, 失敗: False
    """
    try:
        calendar_id = CALENDAR_IDS.get(data['calendar'])
        if not calendar_id:
            log('ERROR', '不正なカレンダー名', {'calendar': data['calendar']})
            return False

        # イベント作成
        if data.get('is_all_day'):
            # 終日イベント
            from datetime import datetime, timedelta
            start_date = data['date']
            # 終了日は翌日（Google Calendarの仕様）
            end_date_obj = datetime.strptime(data['date'], '%Y-%m-%d') + timedelta(days=1)
            end_date = end_date_obj.strftime('%Y-%m-%d')

            event = {
                'summary': data['summary'],
                'description': 'Discordからclaude_codeにより登録されたイベント',
                'start': {
                    'date': start_date,
                },
                'end': {
                    'date': end_date,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1日前（当日朝）
                    ],
                },
            }
        else:
            # 時刻指定イベント
            start_datetime = f"{data['date']}T{data['start_time']}:00"
            end_datetime = f"{data['date']}T{data['end_time']}:00"

            event = {
                'summary': data['summary'],
                'description': 'Discordからclaude_codeにより登録されたイベント',
                'start': {
                    'dateTime': start_datetime,
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_datetime,
                    'timeZone': 'Asia/Tokyo',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1日前
                        {'method': 'popup', 'minutes': 3 * 60},   # 3時間前
                        {'method': 'popup', 'minutes': 2 * 60},   # 2時間前
                        {'method': 'popup', 'minutes': 1 * 60},   # 1時間前
                    ],
                },
            }

        created_event = calendar_service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        # ログ出力
        if data.get('is_all_day'):
            log('INFO', 'Google Calendar登録成功', {
                'calendar': data['calendar'],
                'summary': data['summary'],
                'start': data['date'] + ' (終日)',
                'event_id': created_event.get('id')
            })
        else:
            log('INFO', 'Google Calendar登録成功', {
                'calendar': data['calendar'],
                'summary': data['summary'],
                'start': f"{data['date']}T{data['start_time']}:00",
                'event_id': created_event.get('id')
            })
        return True

    except HttpError as e:
        log('ERROR', 'Google Calendar APIエラー', {'error': str(e)})
        return False
    except Exception as e:
        log('ERROR', 'create_calendar_event例外', {'error': str(e)})
        return False


class CalendarSelectView(discord.ui.View):
    """カレンダー選択ボタンView"""

    def __init__(self, event_data: Dict, original_message: discord.Message):
        super().__init__(timeout=300)  # 5分でタイムアウト
        self.event_data = event_data
        self.original_message = original_message

    @discord.ui.button(label="🏠 プライベート", style=discord.ButtonStyle.primary)
    async def private_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, "プライベート")

    @discord.ui.button(label="⛩️ 祖霊社", style=discord.ButtonStyle.success)
    async def soryo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, "祖霊社")

    @discord.ui.button(label="🏢 本社", style=discord.ButtonStyle.secondary)
    async def honsha_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_selection(interaction, "本社")

    async def handle_selection(self, interaction: discord.Interaction, calendar_name: str):
        """ボタンクリック時の処理"""
        # イベントデータにカレンダーを設定
        self.event_data['calendar'] = calendar_name

        # インタラクションに応答（ローディング表示）
        await interaction.response.defer()

        # カレンダーに登録
        if await create_calendar_event(self.event_data):
            # 成功メッセージ
            if self.event_data.get('is_all_day'):
                result_msg = f"✅ カレンダー登録完了: {self.event_data['summary']} ({self.event_data['date']} 終日) → {calendar_name}"
            else:
                result_msg = f"✅ カレンダー登録完了: {self.event_data['summary']} ({self.event_data['date']} {self.event_data['start_time']}-{self.event_data['end_time']}) → {calendar_name}"
            await interaction.followup.send(result_msg)
            await self.original_message.add_reaction('✅')
            log('INFO', 'カレンダー登録完了', {'calendar': calendar_name})
        else:
            # 失敗メッセージ
            await interaction.followup.send('❌ カレンダー登録に失敗しました')
            await self.original_message.add_reaction('❌')
            log('ERROR', 'カレンダー登録失敗')

        # ボタンを無効化
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)


@bot.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {bot.user}')
    log('INFO', f'カレンダー登録チャンネル監視開始: {CALENDAR_CHANNEL_IDS}')

    # Google Calendar API初期化
    if not init_google_calendar():
        log('ERROR', 'Google Calendar API初期化失敗、Botを終了します')
        await bot.close()


@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # カレンダー登録チャンネル以外のメッセージは無視
    if message.channel.id not in CALENDAR_CHANNEL_IDS:
        return

    # 重複処理防止
    if message.id in processed_messages:
        return

    log('INFO', 'カレンダー登録チャンネルにメッセージ受信', {
        'author': str(message.author),
        'channel': message.channel.name,
        'content': message.content
    })

    # メッセージを解析
    parsed = parse_calendar_message(message.content)

    if parsed:
        log('INFO', 'カレンダー登録開始')

        # カレンダーが指定されている場合は即登録
        if parsed['calendar']:
            if await create_calendar_event(parsed):
                # Discord通知
                if parsed.get('is_all_day'):
                    result_msg = f"✅ カレンダー登録完了: {parsed['summary']} ({parsed['date']} 終日) → {parsed['calendar']}"
                else:
                    result_msg = f"✅ カレンダー登録完了: {parsed['summary']} ({parsed['date']} {parsed['start_time']}-{parsed['end_time']}) → {parsed['calendar']}"
                await message.add_reaction('✅')
                await message.reply(result_msg, mention_author=False)
                log('INFO', 'カレンダー登録完了')
            else:
                await message.add_reaction('❌')
                await message.reply('❌ カレンダー登録に失敗しました', mention_author=False)
                log('ERROR', 'カレンダー登録失敗')
        else:
            # カレンダー選択ボタンを表示
            view = CalendarSelectView(parsed, message)
            if parsed.get('is_all_day'):
                select_msg = f"📅 **{parsed['summary']}**\n日時: {parsed['date']} (終日)\n\nどのカレンダーに登録しますか？"
            else:
                select_msg = f"📅 **{parsed['summary']}**\n日時: {parsed['date']} {parsed['start_time']}-{parsed['end_time']}\n\nどのカレンダーに登録しますか？"
            await message.reply(select_msg, view=view, mention_author=False)
            log('INFO', 'カレンダー選択ボタン表示')
    else:
        log('WARN', 'テキスト解析失敗またはカレンダー情報なし', {'text': message.content})
        await message.add_reaction('❓')
        await message.reply('❓ メッセージ形式が不正です。例: `11/5 10:00 散髪` / `11/5 誕生日` (終日) / `11/5 10:00 散髪 @プライベート`', mention_author=False)

    # 処理済みとして記録
    processed_messages.add(message.id)

    # コマンド処理を継続
    await bot.process_commands(message)


if __name__ == "__main__":
    run_with_retry(bot, DISCORD_TOKEN, 'カレンダーMonitor')
