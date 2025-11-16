#!/usr/bin/env python3
"""
Discordフォーラムチャンネルのスレッド一覧を取得するスクリプト

使用方法:
  python get_forum_threads.py <forum_channel_id>
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

async def get_forum_threads(forum_id: int):
    """フォーラムチャンネルのスレッド一覧を取得"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            forum = await client.fetch_channel(forum_id)

            if not isinstance(forum, discord.ForumChannel):
                print(f"ERROR: このチャンネルはフォーラムではありません", file=sys.stderr)
                await client.close()
                return

            print(f"=== フォーラム: {forum.name} ===\n")

            # アクティブなスレッドを取得
            threads = forum.threads
            archived_threads = []

            # アーカイブされたスレッドも取得
            async for thread in forum.archived_threads(limit=100):
                archived_threads.append(thread)

            all_threads = list(threads) + archived_threads

            print(f"スレッド数: {len(all_threads)}\n")
            print("-" * 80)

            for thread in all_threads:
                print(f"\n📌 {thread.name}")
                print(f"   ID: {thread.id}")
                print(f"   作成日: {thread.created_at.strftime('%Y-%m-%d %H:%M')}")
                print(f"   メッセージ数: {thread.message_count}")
                print(f"   アーカイブ: {'はい' if thread.archived else 'いいえ'}")
                print(f"   ロック: {'はい' if thread.locked else 'いいえ'}")

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        finally:
            await client.close()

    await client.start(TOKEN)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    forum_id = int(sys.argv[1])
    asyncio.run(get_forum_threads(forum_id))

if __name__ == "__main__":
    main()
