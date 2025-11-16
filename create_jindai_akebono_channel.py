#!/usr/bin/env python3
import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKENが.envファイルに設定されていません。")

# Discord bot のインスタンス作成
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORY_ID = 1433208982260027442  # 植物カテゴリ

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        # カテゴリを取得
        category = bot.get_channel(CATEGORY_ID)
        if not category:
            print(f"❌ カテゴリID {CATEGORY_ID} が見つかりません")
            await bot.close()
            return

        if not isinstance(category, discord.CategoryChannel):
            print(f"❌ ID {CATEGORY_ID} はカテゴリチャンネルではありません")
            await bot.close()
            return

        print(f"📁 カテゴリ: {category.name}")

        # チャンネルを作成
        channel = await category.create_text_channel("神代曙")

        print(f"✅ チャンネルを作成しました")
        print(f"   名前: {channel.name}")
        print(f"   ID: {channel.id}")
        print(f"   カテゴリ: {category.name}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
