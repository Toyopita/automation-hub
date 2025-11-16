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

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        # サーバー（ギルド）を取得
        guild = bot.guilds[0] if bot.guilds else None
        if not guild:
            print("❌ サーバーが見つかりません")
            await bot.close()
            return

        print(f"🏠 サーバー: {guild.name}")

        # カテゴリを作成
        category = await guild.create_category("╭── 植物 ──╮")

        print(f"✅ カテゴリを作成しました")
        print(f"   名前: {category.name}")
        print(f"   ID: {category.id}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
