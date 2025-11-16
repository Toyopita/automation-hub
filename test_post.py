#!/usr/bin/env python3
import discord
import os
import asyncio
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1434368052916392076

message = """📅 **2025年11月2日（土）の予定**

━━━━━━━━━━━━━━━━━━━━━━━━

**【六曜】** 先負

━━━━━━━━━━━━━━━━━━━━━━━━

**【本日の予定】**

`09:00 - 15:00` 眞佐國天王大祭（本社）

`10:00 - 11:00` 【仮】冥福祭（冥福祭）

`11:00 - 12:00` 【仮】冥福祭（冥福祭）

━━━━━━━━━━━━━━━━━━━━━━━━

**【締切間近のタスク】**

🔴 プレハブ確認
`期限超過` 10/7 | 日常業務

🔴 文鎮準備
`期限超過` 10/26 | 株式会社双立

⚠️ 神饌発注
`本日期限` 11/1 | 日常業務

📌 前夜祭神饌リスト編集
11/5 | 日常業務

*他26件の未了タスクがあります*

━━━━━━━━━━━━━━━━━━━━━━━━
`自動送信 | 2025-11-02 11:35`
"""

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(message)
        print(f'✅ テストメッセージを投稿しました: #{channel.name}')
    else:
        print(f'❌ チャンネルが見つかりません: {CHANNEL_ID}')

    await client.close()

asyncio.run(client.start(TOKEN))
