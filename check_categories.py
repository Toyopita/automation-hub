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

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    try:
        guild = bot.guilds[0]
        print(f"🏠 サーバー: {guild.name}\n")

        print("【カテゴリ一覧】")
        for category in guild.categories:
            print(f"\n📁 カテゴリ: {category.name} (ID: {category.id})")
            print(f"   権限設定:")
            for target, overwrite in category.overwrites.items():
                if isinstance(target, discord.Role):
                    print(f"     - ロール: {target.name}")
                else:
                    print(f"     - ユーザー: {target.name}")
                print(f"       view_channel: {overwrite.view_channel}")
                print(f"       send_messages: {overwrite.send_messages}")
                print(f"       manage_channels: {overwrite.manage_channels}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
