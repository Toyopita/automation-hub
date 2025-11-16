#!/usr/bin/env python3
"""
Discordチャンネルのメッセージを取得するスクリプト

使用方法:
  python get_channel_messages.py <channel_id> [limit]
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN が必要です")

async def get_messages(channel_id: int, limit: int = 50):
    """チャンネルのメッセージを取得"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            channel = await client.fetch_channel(channel_id)
            print(f"=== チャンネル: {channel.name} ===\n")

            messages = []
            async for message in channel.history(limit=limit):
                messages.append(message)

            # 古い順に表示
            messages.reverse()

            for msg in messages:
                print(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M')}] {msg.author.name}")
                print(f"{msg.content}")
                if msg.attachments:
                    for att in msg.attachments:
                        print(f"📎 {att.url}")
                print("-" * 80)

            print(f"\n取得件数: {len(messages)}")

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
        finally:
            await client.close()

    await client.start(TOKEN)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    channel_id = int(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    asyncio.run(get_messages(channel_id, limit))

if __name__ == "__main__":
    main()
