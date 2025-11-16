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

        # オーナーを取得
        owner_id = guild.owner_id
        owner = guild.get_member(owner_id)
        if not owner:
            owner = await guild.fetch_member(owner_id)
        print(f"👤 オーナー: {owner.name} (ID: {owner.id})")

        # パーミッション設定（カテゴリから継承）
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False,
                view_channel=False
            ),
            owner: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                view_channel=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                view_channel=True,
                manage_channels=True
            )
        }

        # "no name"チャンネルを作成
        channel = await guild.create_text_channel(
            name="no name",
            category=category,
            overwrites=overwrites
        )

        print(f"✅ チャンネル作成成功: {channel.name}")
        print(f"   チャンネルID: {channel.id}")
        print(f"   カテゴリ: {category.name}")
        print(f"   パーミッション: {owner.name}だけが閲覧可能")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
