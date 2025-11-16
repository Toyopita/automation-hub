#!/usr/bin/env python3
import asyncio
import os
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKENが.envファイルに設定されていません。")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = discord.Client(intents=intents)

MUSIC_CATEGORY_ID = 1433376616272363560  # Musicカテゴリ

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    try:
        guild = bot.guilds[0]
        print(f"🏠 サーバー: {guild.name}")

        # Musicカテゴリを取得
        category = guild.get_channel(MUSIC_CATEGORY_ID)
        if not category:
            print(f"❌ Musicカテゴリ (ID: {MUSIC_CATEGORY_ID}) が見つかりません")
            await bot.close()
            return

        print(f"📁 現在のカテゴリ名: {category.name}")

        # カテゴリ名を変更（新しい装飾スタイル）
        await category.edit(name="━━━ Music ━━━")

        print(f"✅ カテゴリ名を変更しました")
        print(f"   新しい名前: ━━━ Music ━━━")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
