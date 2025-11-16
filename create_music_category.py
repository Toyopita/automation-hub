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
        # サーバーを取得（最初のサーバーを使用）
        guild = bot.guilds[0]
        print(f"🏠 サーバー: {guild.name}")

        # オーナーを取得（toyopita）
        owner_id = guild.owner_id
        owner = guild.get_member(owner_id)
        if not owner:
            owner = await guild.fetch_member(owner_id)
        print(f"👤 オーナー: {owner.name} (ID: {owner.id})")

        # パーミッション設定
        # @everyone: すべて拒否（見れない）
        # オーナー: すべて許可（あなただけ見れる）
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False,
                view_channel=False
            ),
            owner: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                view_channel=True,
                manage_channels=True
            )
        }

        # 音楽カテゴリを作成
        category = await guild.create_category(
            name="Music",
            overwrites=overwrites
        )

        print(f"✅ カテゴリ作成成功: {category.name}")
        print(f"   カテゴリID: {category.id}")
        print(f"   パーミッション: {owner.name}だけが閲覧可能")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
