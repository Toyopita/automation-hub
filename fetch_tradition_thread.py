#!/usr/bin/env python3
"""
Discordフォーラムスレッドからメッセージを取得するスクリプト

使用方法:
  python fetch_tradition_thread.py <thread_id>
"""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv
import discord

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN が必要です")

async def fetch_thread_messages(thread_id: int):
    """スレッドの全メッセージを取得してJSON出力"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            thread = await client.fetch_channel(thread_id)

            if not isinstance(thread, discord.Thread):
                print(json.dumps({
                    "error": "指定されたIDはスレッドではありません"
                }, ensure_ascii=False))
                await client.close()
                return

            # スレッドの全メッセージを取得
            messages = []
            async for message in thread.history(limit=100, oldest_first=True):
                messages.append({
                    "id": message.id,
                    "author": str(message.author),
                    "author_id": message.author.id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "is_bot": message.author.bot
                })

            result = {
                "thread_id": thread.id,
                "thread_name": thread.name,
                "message_count": len(messages),
                "messages": messages
            }

            print(json.dumps(result, ensure_ascii=False, indent=2))

        except discord.NotFound:
            print(json.dumps({
                "error": "スレッドが見つかりません"
            }, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({
                "error": str(e)
            }, ensure_ascii=False))
        finally:
            await client.close()

    await client.start(DISCORD_TOKEN)

def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    try:
        thread_id = int(sys.argv[1])
    except ValueError:
        print("ERROR: thread_idは数値である必要があります", file=sys.stderr)
        sys.exit(1)

    asyncio.run(fetch_thread_messages(thread_id))

if __name__ == "__main__":
    main()
