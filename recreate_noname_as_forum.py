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
NONAME_CHANNEL_ID = 1433380599430905979  # 既存のno-nameチャンネル

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
        print(f"📁 カテゴリ: {category.name}")

        # 既存のno-nameチャンネルを削除
        old_channel = guild.get_channel(NONAME_CHANNEL_ID)
        if old_channel:
            await old_channel.delete()
            print(f"🗑️ 既存の「{old_channel.name}」チャンネルを削除しました")

        # 新しくフォーラムチャンネルを作成
        forum_channel = await guild.create_forum(
            name="no name",
            category=category
        )

        print(f"✅ フォーラムチャンネル作成成功: {forum_channel.name}")
        print(f"   チャンネルID: {forum_channel.id}")
        print(f"   タイプ: フォーラム")
        print(f"   カテゴリ: {category.name}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
