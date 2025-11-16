#!/usr/bin/env python3
"""
一時的なスクリプト：タスクメモシステムのお知らせを投稿
"""

import os
import discord
import asyncio

# 環境変数から直接読み込み
with open('/Users/minamitakeshi/discord-mcp-server/.env') as f:
    for line in f:
        if line.startswith('DISCORD_TOKEN='):
            DISCORD_TOKEN = line.strip().split('=', 1)[1]
            break

ANNOUNCEMENT_CHANNEL_ID = 1430791442959433829

message = """# 🗒️ タスクメモ自動化システム運用開始

## 概要
Discordの #🗒️｜タスクメモ チャンネルに投稿したメッセージが、自動的にNotion「祖霊社タスクDB」に登録されるようになりました。

## 使い方
1. #🗒️｜タスクメモ チャンネルにタスク内容を投稿
2. 自動的にNotionに登録され、期限が投稿日（今日）に設定されます
3. 登録完了後、✅リアクションと完了メッセージが返信されます

## 例
```
Discordに投稿: 「会議資料を準備する」
→ Notionに登録: タスク名「会議資料を準備する」、期限「2025-11-01」
```

## 注意事項
- Bot自動化により、投稿内容がそのままタスク名になります
- 期限は投稿日に自動設定されます（変更はNotion上で手動調整してください）
- 空のメッセージは登録されません（❓リアクションが返ります）

---
**技術仕様**: MacBook上で動作（launchdサービス）
**対象チャンネル**: #🗒️｜タスクメモ
**Notion DB**: 祖霊社タスクDB"""

async def main():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Bot起動: {client.user}')
        channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            await channel.send(message)
            print('お知らせ投稿完了')
        else:
            print(f'チャンネルが見つかりません: {ANNOUNCEMENT_CHANNEL_ID}')
        await client.close()

    try:
        await client.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
