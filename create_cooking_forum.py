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
bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORY_ID = 1433046048867221534  # プライベートカテゴリ
CHANNEL_NAME = "料理"

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        category = bot.get_channel(CATEGORY_ID)
        if not category:
            print(f"❌ カテゴリID {CATEGORY_ID} が見つかりません")
            await bot.close()
            return

        if not isinstance(category, discord.CategoryChannel):
            print(f"❌ ID {CATEGORY_ID} はカテゴリではありません")
            await bot.close()
            return

        print(f"📂 カテゴリ: {category.name}")

        # フォーラムチャンネルを作成
        forum_channel = await category.guild.create_forum(
            name=CHANNEL_NAME,
            category=category
        )

        print(f"✅ フォーラムチャンネル「{CHANNEL_NAME}」を作成しました")
        print(f"   チャンネルID: {forum_channel.id}")
        print(f"   カテゴリ: {category.name}")

    except discord.Forbidden:
        print("❌ 権限エラー: Botに「チャンネルの管理」権限が必要です")
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
