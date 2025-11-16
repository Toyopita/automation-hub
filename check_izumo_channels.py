#!/usr/bin/env python3
"""
IZUMOサーバーのチャンネル一覧を取得
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Bot起動: {bot.user}')

    # IZUMOサーバーを検索
    guild = None
    for g in bot.guilds:
        if 'IZUMO' in g.name.upper() or 'イズモ' in g.name:
            guild = g
            break

    if not guild:
        print('エラー: IZUMOサーバーが見つかりません')
        await bot.close()
        return

    print(f'\nサーバー: {guild.name}\n')
    print('=' * 80)

    # カテゴリとチャンネルを表示
    for category in guild.categories:
        print(f'\n📁 カテゴリ: {category.name} (ID: {category.id})')
        for channel in category.channels:
            ch_type = 'フォーラム' if isinstance(channel, discord.ForumChannel) else 'テキスト'
            print(f'  - [{ch_type}] {channel.name} (ID: {channel.id})')

    # カテゴリなしのチャンネル
    print(f'\n📁 カテゴリなし')
    for channel in guild.channels:
        if channel.category is None and isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
            ch_type = 'フォーラム' if isinstance(channel, discord.ForumChannel) else 'テキスト'
            print(f'  - [{ch_type}] {channel.name} (ID: {channel.id})')

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
