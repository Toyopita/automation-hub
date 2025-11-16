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

MUSIC_CATEGORY_ID = 1433376616272363560  # 既存のMusicカテゴリ

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    try:
        guild = bot.guilds[0]
        print(f"🏠 サーバー: {guild.name}")

        # 既存のMusicカテゴリの確認（削除は手動で行う）
        old_category = guild.get_channel(MUSIC_CATEGORY_ID)
        if old_category:
            print(f"⚠️ 既存のMusicカテゴリが存在します")
            print(f"   手動で削除してから再実行してください")
            await bot.close()
            return

        # オーナーを取得
        owner_id = guild.owner_id
        owner = guild.get_member(owner_id)
        if not owner:
            owner = await guild.fetch_member(owner_id)
        print(f"👤 オーナー: {owner.name} (ID: {owner.id})")

        # パーミッション設定（プライベートカテゴリと同様）
        # @everyone: 見れない、オーナー: 見れる
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            owner: discord.PermissionOverwrite(
                view_channel=True
            )
        }

        # 新しいMusicカテゴリを作成（他のカテゴリと同じスタイル）
        category = await guild.create_category(
            name="╭── Music ──╮",
            overwrites=overwrites
        )

        print(f"✅ 新しいMusicカテゴリを作成しました")
        print(f"   カテゴリ名: {category.name}")
        print(f"   カテゴリID: {category.id}")
        print(f"   パーミッション: {owner.name}だけが閲覧可能")

        # "no name"チャンネルを作成
        channel = await guild.create_text_channel(
            name="no name",
            category=category
        )

        print(f"✅ チャンネル作成成功: {channel.name}")
        print(f"   チャンネルID: {channel.id}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

bot.run(TOKEN)
