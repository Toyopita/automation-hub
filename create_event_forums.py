#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord 祭礼・行事フォーラム作成スクリプト
毎年繰り返される祭礼・行事をフォーラム形式で管理
"""

import os
import discord
import asyncio
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# IZUMOサーバーID
IZUMO_GUILD_ID = 1430359607905222658

# カテゴリ名
SAIREI_CATEGORY_NAME = "━━━ 祭礼 ━━━"
GYOJI_CATEGORY_NAME = "━━━ 行事 ━━━"

# 祭礼フォーラム一覧
SAIREI_FORUMS = [
    {
        'name': '📋 物故功労者慰霊祭',
        'description': '毎年開催される物故功労者慰霊祭（周年）の年度別スレッド'
    },
    {
        'name': '📋 例大祭',
        'description': '年度別の例大祭進行スレッド'
    },
    {
        'name': '📋 冥福祭',
        'description': '年度別の冥福祭進行スレッド'
    },
    {
        'name': '📋 夏季御霊祭',
        'description': '年度別の夏季御霊祭進行スレッド'
    },
    {
        'name': '📋 秋季神霊大祭',
        'description': '年度別の秋季神霊大祭進行スレッド'
    },
    {
        'name': '📋 神迎祭',
        'description': '年度別の神迎祭進行スレッド'
    },
    {
        'name': '📋 御霊鎮め',
        'description': '年度別の御霊鎮め進行スレッド'
    },
    {
        'name': '📋 秋季例大祭',
        'description': '年度別の秋季例大祭進行スレッド'
    }
]

# 行事フォーラム一覧
GYOJI_FORUMS = [
    {
        'name': '📋 ひふみ',
        'description': '年度別のひふみ進行スレッド'
    },
    {
        'name': '📋 金剛不動明王月次祭',
        'description': '年度別・月別の金剛不動明王月次祭スレッド'
    },
    {
        'name': '📋 祈りの会',
        'description': '年度別の祈りの会進行スレッド'
    },
    {
        'name': '📋 金剛不動明王開眼祭',
        'description': '金剛不動明王開眼記念祭（周年）の年度別スレッド'
    },
    {
        'name': '📋 月次祭',
        'description': '年度別・月別の月次祭スレッド'
    },
    {
        'name': '📋 感謝祭',
        'description': '年度別の感謝祭進行スレッド'
    },
    {
        'name': '📋 菊和会',
        'description': '年度別の菊和会進行スレッド'
    },
    {
        'name': '📋 分祠長就任記念祝賀会',
        'description': '分祠長就任記念祝賀会（周年）の年度別スレッド'
    }
]

intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'✅ Bot接続成功: {client.user.name}')

    # IZUMOサーバー取得
    guild = client.get_guild(IZUMO_GUILD_ID)
    if not guild:
        print(f'❌ IZUMOサーバーが見つかりません（ID: {IZUMO_GUILD_ID}）')
        await client.close()
        return

    print(f'📁 サーバー: {guild.name}')

    # カテゴリ取得または作成
    sairei_category = None
    gyoji_category = None

    for channel in guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            if channel.name == SAIREI_CATEGORY_NAME:
                sairei_category = channel
            elif channel.name == GYOJI_CATEGORY_NAME:
                gyoji_category = channel

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
        # 既存チャンネルチェック
        existing = discord.utils.get(guild.channels, name=forum_data['name'], category=sairei_category)
        if existing:
            print(f'  ⏭️  {forum_data["name"]} - 既に存在します')
            continue

        # フォーラムチャンネル作成
        try:
            forum = await guild.create_forum(
                name=forum_data['name'],
                category=sairei_category,
                topic=forum_data['description']
            )
            print(f'  ✅ {forum_data["name"]} - 作成完了')
            await asyncio.sleep(1)  # レート制限対策
        except Exception as e:
            print(f'  ❌ {forum_data["name"]} - エラー: {e}')

    print()

    # 行事フォーラム作成
    print(f'🔨 行事フォーラム作成開始...')
    for forum_data in GYOJI_FORUMS:
        # 既存チャンネルチェック
        existing = discord.utils.get(guild.channels, name=forum_data['name'], category=gyoji_category)
        if existing:
            print(f'  ⏭️  {forum_data["name"]} - 既に存在します')
            continue

        # フォーラムチャンネル作成
        try:
            forum = await guild.create_forum(
                name=forum_data['name'],
                category=gyoji_category,
                topic=forum_data['description']
            )
            print(f'  ✅ {forum_data["name"]} - 作成完了')
            await asyncio.sleep(1)  # レート制限対策
        except Exception as e:
            print(f'  ❌ {forum_data["name"]} - エラー: {e}')

    print()
    print('🎉 フォーラム作成完了')

    # macOS通知
    os.system(f'osascript -e \'display notification "祭礼・行事フォーラムの作成が完了しました" with title "Discord設定完了"\'')

    await client.close()


if __name__ == '__main__':
    try:
        client.run(DISCORD_TOKEN)
    except Exception as e:
        print(f'❌ エラー: {e}')
