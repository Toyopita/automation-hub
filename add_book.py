#!/usr/bin/env python3
"""
書籍をDiscordフォーラムに登録
"""

import discord
import asyncio
import os
from datetime import date

# 環境変数から直接読み込み
with open('/Users/minamitakeshi/discord-mcp-server/.env') as f:
    for line in f:
        if line.startswith('DISCORD_TOKEN='):
            DISCORD_TOKEN = line.strip().split('=', 1)[1]
            break

BOOK_FORUM_CHANNEL_ID = 1433964655172124742  # Minamiサーバーの書籍フォーラム

async def add_book():
    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Bot起動: {client.user}')
        channel = client.get_channel(BOOK_FORUM_CHANNEL_ID)

        if not channel:
            print(f'チャンネルが見つかりません: {BOOK_FORUM_CHANNEL_ID}')
            await client.close()
            return

        # 書籍タイトル
        book_title = "照葉樹林文化論"

        # 購入日
        today = date.today().strftime('%Y年%m月%d日')

        # スレッド本文
        content = f"""# 📚 {book_title}

**購入日**: {today}
**ステータス**: 未読

---
メモ・感想などはこのスレッドに追記してください。"""

        # フォーラムにスレッドを作成
        thread = await channel.create_thread(
            name=book_title,
            content=content
        )

        print(f'書籍スレッド作成完了: {book_title}')
        print(f'スレッドURL: {thread.thread.jump_url}')

        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(add_book())
