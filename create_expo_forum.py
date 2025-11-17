#!/usr/bin/env python3
"""
大阪関西万博フォーラムチャンネルを作成
DXカテゴリ内に作成
"""

import discord
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# IZUMOサーバーID
GUILD_ID = 1430359607905222658
# DXカテゴリID
DX_CATEGORY_ID = 1430450907279261747

intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot起動: {client.user}')

    guild = client.get_guild(GUILD_ID)
    if not guild:
        print('エラー: IZUMOサーバーが見つかりません')
        await client.close()
        return

    category = guild.get_channel(DX_CATEGORY_ID)
    if not category:
        print('エラー: DXカテゴリが見つかりません')
        await client.close()
        return

    print(f'カテゴリ: {category.name}')

    # フォーラムチャンネル作成
    forum = await guild.create_forum(
        name='🎡｜大阪関西万博',
        category=category
    )

    print(f'✅ フォーラム作成完了: {forum.name} (ID: {forum.id})')

    await client.close()

client.run(TOKEN)
