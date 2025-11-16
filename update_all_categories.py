#!/usr/bin/env python3
import asyncio
import os
import discord
from dotenv import load_dotenv
import re

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

        print("【カテゴリ名変更】")
        for category in guild.categories:
            old_name = category.name

            # 既存の装飾を削除して、カテゴリ名を抽出
            # ╭── XXX ──╮ や ━━━ XXX ━━━ のような装飾を削除
            clean_name = re.sub(r'^[╭─━═\s]+', '', old_name)
            clean_name = re.sub(r'[╮─━═\s]+$', '', clean_name)
            clean_name = clean_name.strip()

            # 新しい装飾スタイル
            new_name = f"━━━ {clean_name} ━━━"

            try:
                await category.edit(name=new_name)
                print(f"✅ {old_name} → {new_name}")
            except Exception as e:
                print(f"❌ {old_name} の変更に失敗: {e}")

        print(f"\n✅ 全カテゴリの名前を変更しました")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
