#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Discord Bot Token
TOKEN = os.getenv('DISCORD_TOKEN')

# MinamiサーバーのチャンネルID（既知）から、サーバーIDを取得して新規チャンネル作成
KNOWN_CHANNEL_ID = 1435510399763091549  # Minamiサーバーの献品チャンネル

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot起動: {client.user}')

    # 既知のチャンネルからサーバーを取得
    known_channel = client.get_channel(KNOWN_CHANNEL_ID)

    if known_channel is None:
        print(f'エラー: チャンネルID {KNOWN_CHANNEL_ID} が見つかりません')
        await client.close()
        return

    guild = known_channel.guild
    print(f'サーバー名: {guild.name} (ID: {guild.id})')

    # チャンネルが既に存在するかチェック
    existing_channel = discord.utils.get(guild.text_channels, name='📷｜ocrテスト')

    if existing_channel:
        print(f'チャンネルは既に存在します: {existing_channel.name} (ID: {existing_channel.id})')
    else:
        # 新規チャンネル作成
        new_channel = await guild.create_text_channel(
            name='📷｜ocrテスト',
            topic='画像からテキストを認識してGoogleカレンダーに自動登録するテストチャンネル'
        )
        print(f'チャンネル作成完了: {new_channel.name} (ID: {new_channel.id})')

    await client.close()

if __name__ == '__main__':
    client.run(TOKEN)
