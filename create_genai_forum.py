#!/usr/bin/env python3
"""
IZUMOサーバーに「🤖｜生成AI」フォーラムチャンネルを作成
既存の「生成ai」テキストチャンネルを削除して作成
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

OLD_CHANNEL_ID = 1432625120542851213  # 生成ai (テキストチャンネル)
DX_CATEGORY_ID = 1430450907279261747  # ━━━ DX ━━━

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

    print(f'サーバー: {guild.name}')

    try:
        # 既存の「生成ai」チャンネルを削除
        old_channel = guild.get_channel(OLD_CHANNEL_ID)
        if old_channel:
            print(f'既存チャンネル削除中: {old_channel.name}')
            await old_channel.delete()
            print('削除完了')

        # DXカテゴリを取得
        category = guild.get_channel(DX_CATEGORY_ID)
        if not category:
            print('エラー: DXカテゴリが見つかりません')
            await bot.close()
            return

        # フォーラムチャンネル作成
        print('フォーラムチャンネル作成中: 🤖｜生成AI')
        forum = await category.create_forum(
            name='🤖｜生成AI',
            topic='毎日の生成AIニュースと最新情報を共有するフォーラム'
        )
        print(f'フォーラム作成完了: {forum.name} (ID: {forum.id})')
        print('✅ 完了')

    except Exception as e:
        print(f'エラー: {e}')

    await bot.close()


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
