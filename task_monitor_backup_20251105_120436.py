#!/usr/bin/env python3
"""
Discord ⇒ MacBook ⇒ Notion ―― タスクメモ自動登録（Python版）

Discordのテキストチャンネル「#🗒️｜タスクメモ」の投稿を監視し、
メッセージをタスク名としてNotion DBに自動登録します。
期限は投稿日（今日）に設定されます。

タスクメモチャンネルID: 1434168803326951456
Notion祖霊社タスクDB ID: 1c800160-1818-807c-b083-f475eb3a07b9
"""

import os
import json
from datetime import datetime, date
from typing import Optional, Dict
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TASK_CHANNEL_ID = 1434168803326951456  # テキストチャンネル #🗒️｜タスクメモ
NOTION_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 処理済みメッセージIDを記録（重複防止）
processed_messages = set()


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[タスクメモ][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


async def add_to_notion(text: str) -> bool:
    """
    Notion APIを使ってタスクをNotionに登録

    Args:
        text: タスク名（Discordメッセージのテキスト）

    Returns:
        成功: True, 失敗: False
    """
    try:
        # テキストの検証
        if not text or text.strip() == '':
            log('ERROR', 'テキストが空または未定義')
            return False

        # Notion統合トークンを環境変数から取得
        notion_token = os.getenv("NOTION_TOKEN_TASK")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_TASKが設定されていません')
            return False

        # 今日の日付を取得（YYYY-MM-DD形式）
        today = date.today().isoformat()
        log('INFO', '期限設定', {'deadline': today})

        properties = {
            "タスク名": {
                "title": [{
                    "type": "text",
                    "text": {"content": text.strip()}
                }]
            },
            "期限": {
                "date": {"start": today}
            }
        }

        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": properties
        }

        log('DEBUG', '送信ペイロード', payload)

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

        log('INFO', 'Notion APIレスポンス', {'code': response.status_code})

        if response.status_code >= 400:
            error_detail = response.json()
            log('ERROR', 'Notion APIエラー', {
                'code': response.status_code,
                'message': error_detail.get('message'),
                'body': error_detail
            })
            return False
        else:
            log('SUCCESS', 'Notion登録成功', {
                'code': response.status_code,
                'task': text,
                'deadline': today
            })

            # 作成されたページの期限プロパティを確認
            try:
                page_data = response.json()
                if page_data.get('properties', {}).get('期限'):
                    log('SUCCESS', '期限プロパティ確認', page_data['properties']['期限'])
            except Exception as e:
                log('WARN', 'レスポンス解析エラー', {'error': str(e)})

            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外', {'error': str(err)})
        return False


@bot.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {bot.user}')
    log('INFO', f'タスクメモチャンネル監視開始: {TASK_CHANNEL_ID}')


@bot.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # タスクメモチャンネル以外のメッセージは無視
    if message.channel.id != TASK_CHANNEL_ID:
        return

    # 重複処理防止
    if message.id in processed_messages:
        return

    log('INFO', 'タスクメモチャンネルにメッセージ受信', {
        'author': str(message.author),
        'channel': message.channel.name,
        'content': message.content[:100]
    })

    # メッセージをタスクとして登録
    message_text = message.content.strip()

    if not message_text:
        log('WARN', 'メッセージが空')
        await message.add_reaction('❓')
        processed_messages.add(message.id)
        return

    log('INFO', 'Notion登録開始', {'message': message_text})

    if await add_to_notion(message_text):
        # Discord通知
        await message.add_reaction('✅')
        today = date.today().strftime('%Y年%m月%d日')
        await message.reply(
            f"✅ タスク登録完了\n📝 タスク名: {message_text}\n📅 期限: {today}",
            mention_author=False
        )
        log('SUCCESS', 'タスク作成成功', {'task': message_text, 'deadline': today})
    else:
        await message.add_reaction('❌')
        log('ERROR', 'タスク作成失敗', {'task': message_text})

    # 処理済みとして記録
    processed_messages.add(message.id)

    # コマンド処理を継続
    await bot.process_commands(message)


if __name__ == "__main__":
    log('INFO', 'タスクメモ監視Bot起動中...')
    bot.run(DISCORD_TOKEN)
