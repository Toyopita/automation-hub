#!/usr/bin/env python3
"""
Discord ⇒ MacBook ⇒ Notion ―― 献酒仕分け職人（Python版）

Discordのテキストチャンネル「#🍶｜献酒」の投稿を監視し、
献酒情報を解析してNotion DBに自動登録します。

献酒チャンネルID: 1430362136726605876
Notion献酒DB ID: 18700160-1818-802b-afef-d94a672cee11
"""

import os
import re
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SAKE_CHANNEL_ID = 1430362136726605876  # テキストチャンネル #🍶｜献酒（献品カテゴリ内）
NOTION_DB_ID = "18700160-1818-802b-afef-d94a672cee11"

# 献酒の種類
SAKE_NAMES = ['賀茂鶴', '樽酒', '上撰', '飛翔', '典雅', 'その他']

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 処理済みメッセージIDを記録（重複防止）
PROCESSED_MESSAGES_FILE = '/Users/minamitakeshi/discord-mcp-server/sake_processed_messages.json'
processed_messages = set()


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[献酒][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


def load_processed_messages():
    """処理済みメッセージIDをファイルから読み込む（30日以内のもののみ）"""
    global processed_messages
    if not os.path.exists(PROCESSED_MESSAGES_FILE):
        processed_messages = set()
        return

    try:
        with open(PROCESSED_MESSAGES_FILE, 'r') as f:
            data = json.load(f)

        # 30日より古い記録を削除
        cutoff_timestamp = (datetime.now().timestamp() - (30 * 24 * 60 * 60)) * 1000  # DiscordのメッセージIDはミリ秒
        processed_messages = {msg_id for msg_id in data if int(msg_id) > cutoff_timestamp}

        log('INFO', f'処理済みメッセージ読み込み: {len(processed_messages)}件')
    except Exception as e:
        log('ERROR', f'処理済みメッセージ読み込みエラー: {e}')
        processed_messages = set()


def save_processed_messages():
    """処理済みメッセージIDをファイルに保存"""
    try:
        with open(PROCESSED_MESSAGES_FILE, 'w') as f:
            json.dump(list(processed_messages), f)
        log('DEBUG', f'処理済みメッセージ保存: {len(processed_messages)}件')
    except Exception as e:
        log('ERROR', f'処理済みメッセージ保存エラー: {e}')


def parse_sake(text: str) -> Optional[Dict]:
    """
    献酒メッセージを解析

    Args:
        text: Discordメッセージのテキスト

    Returns:
        解析結果の辞書 or None
        {'year': '2025', 'month': '1', 'dept': '本部', 'items': [{'name': '賀茂鶴', 'qty': 1000}, ...]}
    """
    try:
        log('DEBUG', '解析開始', {'text': text})

        # 全角数字を半角に変換
        text = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # 年月、部署を抽出
        year_match = re.search(r'(\d{4})年', text)
        month_match = re.search(r'(\d{1,2})月', text)
        dept_match = re.search(r'(本部|祖霊社)', text)

        year = year_match.group(1) if year_match else ''
        month = month_match.group(1) if month_match else ''
        dept = dept_match.group(1) if dept_match else ''

        # 各献酒の数量を抽出
        items = []
        for name in SAKE_NAMES:
            # 商品名直後の数値を取得（柔軟なパターンマッチング）
            regex = re.compile(rf'{name}[\s:：]*[^0-9]*?(\d+)', re.IGNORECASE)
            for m in regex.finditer(text):
                qty = int(m.group(1))
                if qty > 0:  # 0より大きい数量のみ登録
                    items.append({'name': name, 'qty': qty})

        result = {'year': year, 'month': month, 'dept': dept, 'items': items} if items else None
        log('DEBUG', '解析結果', result)
        return result

    except Exception as err:
        log('ERROR', 'parseSake例外', {'error': str(err)})
        return None


async def push_to_notion_sake(data: Dict, item: Dict) -> bool:
    """
    Notion APIを使って献酒データをNotionに登録

    Args:
        data: 解析済みデータ（year, month, dept）
        item: 個別アイテム（name, qty）

    Returns:
        成功: True, 失敗: False
    """
    try:
        # Notion統合トークンを環境変数から取得
        notion_token = os.getenv("NOTION_TOKEN_SAKE")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_SAKEが設定されていません')
            return False

        properties = {
            "分類": {
                "select": {"name": data['dept'] or "未設定"}
            },
            "奉納年": {
                "select": {"name": data['year'] or "未設定"}
            },
            "奉納月": {
                "select": {"name": data['month'] or "未設定"}
            },
            "商品名": {
                "title": [{
                    "type": "text",
                    "text": {"content": item['name']}
                }]
            },
            "数量": {
                "number": item['qty']
            }
        }

        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": properties
        }

        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            'https://api.notion.com/v1/pages',
            headers=headers,
            json=payload
        )

        if response.status_code >= 400:
            error_detail = response.json()
            log('ERROR', 'Notion APIエラー', {
                'code': response.status_code,
                'message': error_detail.get('message'),
                'item': item
            })
            return False
        else:
            log('INFO', 'Notion登録成功', {'code': response.status_code, 'item': item})
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外', {'error': str(err)})
        return False


@bot.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {bot.user}')
    log('INFO', f'献酒チャンネル監視開始: {SAKE_CHANNEL_ID}')

    # 処理済みメッセージを読み込む
    load_processed_messages()


@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # 献酒チャンネル以外のメッセージは無視
    if message.channel.id != SAKE_CHANNEL_ID:
        return

    # 重複処理防止
    if message.id in processed_messages:
        return

    log('INFO', '献酒チャンネルにメッセージ受信', {
        'author': str(message.author),
        'channel': message.channel.name,
        'content': message.content[:100]
    })

    # メッセージを解析
    parsed = parse_sake(message.content)

    if parsed and parsed['items']:
        log('INFO', f"{len(parsed['items'])}件のアイテムを登録開始")

        success_count = 0
        for item in parsed['items']:
            if await push_to_notion_sake(parsed, item):
                success_count += 1

        # Discord通知
        result_msg = f"✅ 献酒登録完了: {success_count}/{len(parsed['items'])}件"
        await message.add_reaction('✅')
        await message.reply(result_msg, mention_author=False)

        log('INFO', f'登録完了: {success_count}/{len(parsed["items"])}件')
    else:
        log('WARN', 'テキスト解析失敗または献酒情報なし', {'text': message.content})
        await message.add_reaction('❓')

    # 処理済みとして記録
    processed_messages.add(message.id)
    save_processed_messages()

    # コマンド処理を継続
    await bot.process_commands(message)


if __name__ == "__main__":
    log('INFO', '献酒監視Bot起動中...')
    bot.run(DISCORD_TOKEN)
