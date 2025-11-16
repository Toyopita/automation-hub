"""
Discord Bot でアクセス可能なチャンネル一覧を取得
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# 環境変数読み込み
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot初期化
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}\n")
    print("=" * 80)
    print("Discord サーバーとチャンネルの一覧")
    print("=" * 80)

    for guild in bot.guilds:
        print(f"\n📁 サーバー: {guild.name} (ID: {guild.id})")
        print(f"   メンバー数: {guild.member_count}")
        print(f"   チャンネル数: {len(guild.channels)}")
        print("-" * 80)

        # テキストチャンネル
        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
        if text_channels:
            print("   📝 テキストチャンネル:")
            for channel in text_channels:
                print(f"      #{channel.name}")
                print(f"        ID: {channel.id}")
                print(f"        カテゴリ: {channel.category.name if channel.category else 'なし'}")

        # ボイスチャンネル
        voice_channels = [ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)]
        if voice_channels:
            print("   🔊 ボイスチャンネル:")
            for channel in voice_channels:
                print(f"      🔊 {channel.name}")
                print(f"        ID: {channel.id}")

        # フォーラムチャンネル
        forum_channels = [ch for ch in guild.channels if isinstance(ch, discord.ForumChannel)]
        if forum_channels:
            print("   💬 フォーラムチャンネル:")
            for channel in forum_channels:
                print(f"      💬 {channel.name}")
                print(f"        ID: {channel.id}")
                print(f"        カテゴリ: {channel.category.name if channel.category else 'なし'}")

        # カテゴリ
        categories = [ch for ch in guild.channels if isinstance(ch, discord.CategoryChannel)]
        if categories:
            print("   📂 カテゴリ:")
            for category in categories:
                print(f"      📂 {category.name}")
                print(f"        ID: {category.id}")

    print("\n" + "=" * 80)
    print("取得完了")
    print("=" * 80)

    # Bot停止
    await bot.close()


if __name__ == "__main__":
    asyncio.run(bot.start(DISCORD_BOT_TOKEN))
