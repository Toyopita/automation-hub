#!/usr/bin/env python3
"""
献品テストチャンネル作成スクリプト
"""

import os
import discord
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot起動: {client.user}')

    for guild in client.guilds:
        print(f'サーバー: {guild.name}')

        # 既存の「献品テスト」チャンネルを探す
        existing_channel = None
        for channel in guild.text_channels:
            if channel.name == '🍶🌾｜献品テスト':
                existing_channel = channel
                print(f'既存のチャンネル発見: {channel.name} (ID: {channel.id})')
                break

        if not existing_channel:
            # チャンネルを作成
            try:
                new_channel = await guild.create_text_channel('🍶🌾｜献品テスト')
                print(f'チャンネル作成完了: {new_channel.name} (ID: {new_channel.id})')
            except Exception as e:
                print(f'チャンネル作成失敗: {e}')

    await client.close()

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
