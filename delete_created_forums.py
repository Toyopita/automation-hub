#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord 作成したフォーラムとカテゴリを削除
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

# 削除対象カテゴリ
DELETE_CATEGORIES = [
    "━━━ 祭礼 ━━━",
    "━━━ 行事 ━━━"
]

intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'✅ Bot接続成功: {client.user.name}')

    guild = client.get_guild(IZUMO_GUILD_ID)
    if not guild:
        print(f'❌ サーバーが見つかりません')
        await client.close()
        return

    print(f'📁 サーバー: {guild.name}\n')

    for category_name in DELETE_CATEGORIES:
        category = discord.utils.get(guild.categories, name=category_name)

        if not category:
            print(f'⏭️  {category_name} - カテゴリが見つかりません')
            continue

        print(f'🗑️  {category_name} を削除します...')

        # カテゴリ内の全チャンネルを削除
        for channel in category.channels:
            try:
                await channel.delete()
                print(f'  ✅ {channel.name} - 削除完了')
                await asyncio.sleep(1)
            except Exception as e:
                print(f'  ❌ {channel.name} - エラー: {e}')

        # カテゴリ自体を削除
        try:
            await category.delete()
            print(f'  ✅ カテゴリ削除完了\n')
            await asyncio.sleep(1)
        except Exception as e:
            print(f'  ❌ カテゴリ削除エラー: {e}\n')

    print('🎉 削除完了')
    os.system(f'osascript -e \'display notification "フォーラムとカテゴリの削除が完了しました" with title "Discord削除完了"\'')

    await client.close()


if __name__ == '__main__':
    try:
        client.run(TOKEN)
    except Exception as e:
        print(f'❌ エラー: {e}')
