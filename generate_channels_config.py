#!/usr/bin/env python3
"""
Discordのチャンネル情報を取得してchannels.py定数ファイルを生成するスクリプト

使用方法:
  python generate_channels_config.py
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# 環境変数読み込み
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot初期化
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    print("チャンネル情報を取得中...\n")

    output_lines = []
    output_lines.append('"""')
    output_lines.append('Discordチャンネル定数ファイル')
    output_lines.append(f'自動生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    output_lines.append('')
    output_lines.append('使用方法:')
    output_lines.append('  from channels import CHANNELS, FORUMS')
    output_lines.append('  channel_id = CHANNELS["ルール"]')
    output_lines.append('  forum_id = FORUMS["朝刊太郎のチュートリアル"]')
    output_lines.append('"""')
    output_lines.append('')

    for guild in bot.guilds:
        output_lines.append(f'# サーバー: {guild.name}')
        output_lines.append('')

        # テキストチャンネル
        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
        if text_channels:
            output_lines.append('# テキストチャンネル')
            output_lines.append('CHANNELS = {')
            for channel in sorted(text_channels, key=lambda x: x.name):
                # 名前から特殊文字を除去してキーにする
                clean_name = channel.name.replace('🧃｜', '').replace('📖｜', '').replace('🈯', '').replace('🌾｜', '').replace('🍶｜', '').replace('｜', '').replace('📋｜', '').replace('🪦｜', '').replace('🌅｜', '').replace('🛠️', '').replace('🔔｜', '').replace('📰｜', '')
                category = f' ({channel.category.name})' if channel.category else ''
                output_lines.append(f'    "{clean_name}": {channel.id},  # {channel.name}{category}')
            output_lines.append('}')
            output_lines.append('')

        # フォーラムチャンネル
        forum_channels = [ch for ch in guild.channels if isinstance(ch, discord.ForumChannel)]
        if forum_channels:
            output_lines.append('# フォーラムチャンネル')
            output_lines.append('FORUMS = {')
            for channel in sorted(forum_channels, key=lambda x: x.name):
                # 名前から特殊文字を除去してキーにする
                clean_name = channel.name.replace('🤖｜', '').replace('｜', '')
                category = f' ({channel.category.name})' if channel.category else ''
                output_lines.append(f'    "{clean_name}": {channel.id},  # {channel.name}{category}')
            output_lines.append('}')
            output_lines.append('')

        # カテゴリ
        categories = [ch for ch in guild.channels if isinstance(ch, discord.CategoryChannel)]
        if categories:
            output_lines.append('# カテゴリ')
            output_lines.append('CATEGORIES = {')
            for category in sorted(categories, key=lambda x: x.name):
                clean_name = category.name.replace('╭── ', '').replace(' ──╮', '')
                output_lines.append(f'    "{clean_name}": {category.id},  # {category.name}')
            output_lines.append('}')
            output_lines.append('')

        # ボイスチャンネル
        voice_channels = [ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)]
        if voice_channels:
            output_lines.append('# ボイスチャンネル')
            output_lines.append('VOICE_CHANNELS = {')
            for channel in sorted(voice_channels, key=lambda x: x.name):
                category = f' ({channel.category.name})' if channel.category else ''
                output_lines.append(f'    "{channel.name}": {channel.id},{category}')
            output_lines.append('}')
            output_lines.append('')

    # channels.pyに書き込み
    output_file = 'channels.py'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f'✅ {output_file} を生成しました')
    print(f'   テキストチャンネル: {len(text_channels)}')
    print(f'   フォーラムチャンネル: {len(forum_channels)}')
    print(f'   カテゴリ: {len(categories)}')
    print(f'   ボイスチャンネル: {len(voice_channels)}')

    # Bot停止
    await bot.close()


if __name__ == "__main__":
    asyncio.run(bot.start(DISCORD_BOT_TOKEN))
