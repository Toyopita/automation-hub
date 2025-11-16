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

FORUM_ID = 1433053243667251270  # 料理フォーラム

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        forum = bot.get_channel(FORUM_ID)
        if not forum:
            print(f"❌ フォーラムID {FORUM_ID} が見つかりません")
            await bot.close()
            return

        print(f"\n💬 フォーラム: {forum.name}")
        print(f"   カテゴリ: {forum.category.name if forum.category else 'なし'}")
        print(f"\n📋 権限設定:")
        print("=" * 80)

        # @everyone ロールの権限を確認
        guild = forum.guild
        everyone_role = guild.default_role

        overwrites = forum.overwrites

        if everyone_role in overwrites:
            perms = overwrites[everyone_role]
            print(f"\n🌍 @everyone の権限:")
            print(f"   チャンネルを見る: {perms.view_channel}")
            print(f"   メッセージを送信: {perms.send_messages}")
            print(f"   メッセージを読む: {perms.read_messages}")
        else:
            print(f"\n🌍 @everyone: 権限オーバーライドなし（カテゴリから継承）")

            # カテゴリの権限を確認
            if forum.category:
                cat_overwrites = forum.category.overwrites
                if everyone_role in cat_overwrites:
                    perms = cat_overwrites[everyone_role]
                    print(f"\n📂 カテゴリ「{forum.category.name}」の @everyone 権限:")
                    print(f"   チャンネルを見る: {perms.view_channel}")
                    print(f"   メッセージを送信: {perms.send_messages}")
                    print(f"   メッセージを読む: {perms.read_messages}")

        # その他の権限オーバーライドを表示
        print(f"\n👥 その他の権限オーバーライド:")
        for target, perms in overwrites.items():
            if target != everyone_role:
                target_name = target.name if hasattr(target, 'name') else str(target)
                print(f"   {target_name}:")
                print(f"      チャンネルを見る: {perms.view_channel}")
                print(f"      メッセージを送信: {perms.send_messages}")

        print("\n" + "=" * 80)

        # 結論
        if everyone_role in overwrites:
            if overwrites[everyone_role].view_channel == False:
                print("✅ このチャンネルは @everyone から隠されています")
            else:
                print("⚠️  このチャンネルは @everyone に表示されています")
        elif forum.category and everyone_role in forum.category.overwrites:
            if forum.category.overwrites[everyone_role].view_channel == False:
                print("✅ カテゴリ権限により、このチャンネルは @everyone から隠されています")
            else:
                print("⚠️  カテゴリ権限により、このチャンネルは @everyone に表示されています")
        else:
            print("⚠️  権限設定が不明確です")

    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
