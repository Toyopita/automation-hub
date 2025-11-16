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

CHANNEL_ID = 1433209271318741044  # 神代曙チャンネル

RECORD_MESSAGE = """## 📝 水やり記録

**日付**: 2025年9月26日
**対応**: 水やり停止

**理由**: 根腐れの心配のため

**温度変化**:
- 9月25日: 30.17℃（最後の水やり）
- 9月26日: 28.17℃（約2℃低下）

9月26日以降、気温が下がってきたため水やりを停止しました。
根腐れを防ぐため、しばらく様子を見ます。"""

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print(f"❌ チャンネルID {CHANNEL_ID} が見つかりません")
            await bot.close()
            return

        if not isinstance(channel, discord.TextChannel):
            print(f"❌ ID {CHANNEL_ID} はテキストチャンネルではありません")
            await bot.close()
            return

        print(f"💬 チャンネル: {channel.name}")

        # メッセージを投稿
        await channel.send(RECORD_MESSAGE)

        print(f"✅ 水やり記録を投稿しました")
        print(f"   チャンネル: {channel.name}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
