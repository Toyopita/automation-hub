#!/usr/bin/env python3
"""
Discordチャンネルから未処理のメッセージを取得するスクリプト

使用方法:
  python fetch_unprocessed_traditions.py [channel_id] [limit]

  channel_id: 省略時は伝承投稿チャンネル（1438876441226903673）
  limit: 省略時は50件
"""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv
import discord

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DEFAULT_TRADITION_CHANNEL_ID = 1438876441226903673  # 📖｜伝承投稿

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN が必要です")

async def fetch_unprocessed_messages(channel_id: int, limit: int = 50):
    """チャンネルから未処理のメッセージを取得してJSON出力"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            channel = await client.fetch_channel(channel_id)

            if not isinstance(channel, discord.TextChannel):
                print(json.dumps({
                    "error": "指定されたIDはテキストチャンネルではありません"
                }, ensure_ascii=False))
                await client.close()
                return

            # 未処理メッセージを取得（✅リアクションがないもの）
            unprocessed_messages = []
            async for message in channel.history(limit=limit * 2):  # Botメッセージを考慮して多めに取得
                # Botのメッセージは除外
                if message.author.bot:
                    continue

                # ✅リアクションがあれば処理済み
                has_check = any(
                    reaction.emoji == '✅'
                    for reaction in message.reactions
                )

                if not has_check:
                    unprocessed_messages.append({
                        "id": message.id,
                        "author": str(message.author),
                        "author_id": message.author.id,
                        "content": message.content,
                        "created_at": message.created_at.isoformat(),
                        "jump_url": message.jump_url
                    })

                    if len(unprocessed_messages) >= limit:
                        break

            result = {
                "channel_id": channel.id,
                "channel_name": channel.name,
                "unprocessed_count": len(unprocessed_messages),
                "messages": unprocessed_messages
            }

            print(json.dumps(result, ensure_ascii=False, indent=2))

        except discord.NotFound:
            print(json.dumps({
                "error": "チャンネルが見つかりません"
            }, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({
                "error": str(e)
            }, ensure_ascii=False))
        finally:
            await client.close()

    await client.start(DISCORD_TOKEN)

def main():
    # 引数からチャンネルIDと件数を取得
    channel_id = DEFAULT_TRADITION_CHANNEL_ID
    limit = 50

    if len(sys.argv) >= 2:
        try:
            channel_id = int(sys.argv[1])
        except ValueError:
            print("ERROR: channel_idは数値である必要があります", file=sys.stderr)
            sys.exit(1)

    if len(sys.argv) >= 3:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            print("ERROR: limitは数値である必要があります", file=sys.stderr)
            sys.exit(1)

    asyncio.run(fetch_unprocessed_messages(channel_id, limit))

if __name__ == "__main__":
    main()
