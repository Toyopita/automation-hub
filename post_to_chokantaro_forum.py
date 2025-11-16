#!/usr/bin/env python3
"""
朝刊太郎フォーラムに投稿するスクリプト
"""

import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
FORUM_CHANNEL_ID = 1430855994761805874  # 朝刊太郎のチュートリアル

if not TOKEN:
    raise ValueError("DISCORD_TOKEN が必要です")

async def create_thread():
    """スレッドを作成して投稿"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            forum_channel = await client.fetch_channel(FORUM_CHANNEL_ID)

            if isinstance(forum_channel, discord.ForumChannel):
                # スレッド作成（最初のメッセージ）
                thread_with_message = await forum_channel.create_thread(
                    name="朝刊太郎の使い方",
                    content="ここで朝刊太郎の使い方のチュートリアルが確認できます。\n\nhttps://www.chokantaro.com/help/1.チュートリアル.html"
                )

                thread = thread_with_message.thread
                print(f"✅ スレッド作成: {thread.name} (ID: {thread.id})")

                # 2つ目のメッセージを投稿
                await asyncio.sleep(2)
                await thread.send("自由度高く新聞紙面を作れる上に無料とあって2万ダウンロードされているようです。")
                print("✅ 2つ目のメッセージ投稿完了")

            else:
                print("ERROR: Not a forum channel")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await client.close()

    await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(create_thread())
