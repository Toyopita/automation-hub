#!/usr/bin/env python3
"""
notion → 🤖｜Notion にリネーム
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

NOTION_FORUM_ID = 1434339945656487997

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Bot起動: {bot.user}')

    try:
        forum = bot.get_channel(NOTION_FORUM_ID)
        if not forum:
            print(f'エラー: フォーラムが見つかりません (ID: {NOTION_FORUM_ID})')
            await bot.close()
            return

        print(f'現在の名前: {forum.name}')

        # 名前を変更
        await forum.edit(name='🤖｜Notion')
        print(f'変更後の名前: 🤖｜Notion')
        print('✅ 完了')

    except Exception as e:
        print(f'エラー: {e}')

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
