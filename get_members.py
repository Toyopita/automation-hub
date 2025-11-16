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
intents.members = True  # メンバー情報を取得
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    try:
        guild = bot.guilds[0]
        print(f"🏠 サーバー: {guild.name}")
        print(f"📊 メンバー数: {guild.member_count}")
        print(f"👑 オーナーID: {guild.owner_id}")

        print("\n【メンバー一覧】")
        for member in guild.members:
            print(f"  - {member.name} (ID: {member.id}) {'[Bot]' if member.bot else '[User]'}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
