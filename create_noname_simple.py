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
        # サーバーを取得
        guild = bot.guilds[0]
        print(f"🏠 サーバー: {guild.name}")

        # Musicカテゴリを取得
        category = guild.get_channel(MUSIC_CATEGORY_ID)
        if not category:
            print(f"❌ Musicカテゴリ (ID: {MUSIC_CATEGORY_ID}) が見つかりません")
            await bot.close()
            return
        print(f"📁 カテゴリ: {category.name}")

        # カテゴリの現在のoverwritesを確認
        print(f"\n【カテゴリのパーミッション設定】")
        for target, overwrite in category.overwrites.items():
            if isinstance(target, discord.Role):
                print(f"  ロール: {target.name}")
            elif isinstance(target, discord.Member):
                print(f"  メンバー: {target.name}")
            else:
                print(f"  その他: {target}")
            print(f"    view_channel: {overwrite.view_channel}")
            print(f"    manage_channels: {overwrite.manage_channels}")

        # カテゴリのoverwritesをそのまま使ってチャンネルを作成
        channel = await guild.create_text_channel(
            name="no name",
            category=category
        )

        print(f"\n✅ チャンネル作成成功: {channel.name}")
        print(f"   チャンネルID: {channel.id}")
        print(f"   カテゴリ: {category.name}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
