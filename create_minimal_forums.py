#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord 最小限のフォーラム作成（現在進行中のもののみ）
"""

import os
import discord
import asyncio

TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
    with open('.env') as f:
        for line in f:
            if line.startswith('DISCORD_TOKEN='):
                TOKEN = line.strip().split('=', 1)[1]

IZUMO_GUILD_ID = 1430359607905222658

# カテゴリ名
SAIREI_CATEGORY_NAME = "━━━ 祭礼 ━━━"
GYOJI_CATEGORY_NAME = "━━━ 行事 ━━━"

# 最小限のフォーラム
SAIREI_FORUMS = [
    {
        'name': '📋 秋季神霊大祭',
        'description': '年度別の秋季神霊大祭進行スレッド'
    }
]

GYOJI_FORUMS = [
    {
        'name': '📋 神迎祭',
        'description': '年度別の神迎祭進行スレッド'
    }
]

intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'✅ Bot接続成功: {client.user.name}')

    guild = client.get_guild(IZUMO_GUILD_ID)
    if not guild:
        print(f'❌ IZUMOサーバーが見つかりません')
        await client.close()
        return

    print(f'📁 サーバー: {guild.name}\n')

    # カテゴリ取得または作成
    sairei_category = discord.utils.get(guild.categories, name=SAIREI_CATEGORY_NAME)
    gyoji_category = discord.utils.get(guild.categories, name=GYOJI_CATEGORY_NAME)

    # 祭礼カテゴリ作成
    if not sairei_category:
        print(f'🔨 {SAIREI_CATEGORY_NAME} カテゴリを作成します...')
        try:
            sairei_category = await guild.create_category(SAIREI_CATEGORY_NAME)
            print(f'  ✅ カテゴリ作成完了')
            await asyncio.sleep(1)
        except Exception as e:
            print(f'  ❌ カテゴリ作成エラー: {e}')
            await client.close()
            return
    else:
        print(f'✅ {SAIREI_CATEGORY_NAME} カテゴリ確認完了')

    # 行事カテゴリ作成
    if not gyoji_category:
        print(f'🔨 {GYOJI_CATEGORY_NAME} カテゴリを作成します...')
        try:
            gyoji_category = await guild.create_category(GYOJI_CATEGORY_NAME)
            print(f'  ✅ カテゴリ作成完了')
            await asyncio.sleep(1)
        except Exception as e:
            print(f'  ❌ カテゴリ作成エラー: {e}')
            await client.close()
            return
    else:
        print(f'✅ {GYOJI_CATEGORY_NAME} カテゴリ確認完了')

    print()

    # 祭礼フォーラム作成
    print(f'🔨 祭礼フォーラム作成開始...')
    for forum_data in SAIREI_FORUMS:
        existing = discord.utils.get(guild.channels, name=forum_data['name'], category=sairei_category)
        if existing:
            print(f'  ⏭️  {forum_data["name"]} - 既に存在します')
            continue

        try:
            forum = await guild.create_forum(
                name=forum_data['name'],
                category=sairei_category,
                topic=forum_data['description']
            )
            print(f'  ✅ {forum_data["name"]} - 作成完了')
            await asyncio.sleep(1)
        except Exception as e:
            print(f'  ❌ {forum_data["name"]} - エラー: {e}')

    print()

    # 行事フォーラム作成
    print(f'🔨 行事フォーラム作成開始...')
    for forum_data in GYOJI_FORUMS:
        existing = discord.utils.get(guild.channels, name=forum_data['name'], category=gyoji_category)
        if existing:
            print(f'  ⏭️  {forum_data["name"]} - 既に存在します')
            continue

        try:
            forum = await guild.create_forum(
                name=forum_data['name'],
                category=gyoji_category,
                topic=forum_data['description']
            )
            print(f'  ✅ {forum_data["name"]} - 作成完了')
            await asyncio.sleep(1)
        except Exception as e:
            print(f'  ❌ {forum_data["name"]} - エラー: {e}')

    print()
    print('🎉 フォーラム作成完了')

    os.system(f'osascript -e \'display notification "最小限のフォーラムを作成しました" with title "Discord設定完了"\'')

    await client.close()


if __name__ == '__main__':
    try:
        client.run(TOKEN)
    except Exception as e:
        print(f'❌ エラー: {e}')
