#!/usr/bin/env python3
"""
DiscordでClaudeとCodexのリアルタイム対談を投稿するスクリプト

使用方法:
  # スレッド作成（Claude bot）- メッセージは標準入力から
  echo "最初のメッセージ" | python post_debate_realtime.py create_thread "スレッドタイトル"

  # メッセージ投稿（Claude bot）- メッセージは標準入力から
  echo "メッセージ内容" | python post_debate_realtime.py post_claude <thread_id>

  # メッセージ投稿（Codex bot）- メッセージは標準入力から
  echo "メッセージ内容" | python post_debate_realtime.py post_codex <thread_id>
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import discord

load_dotenv()
CLAUDE_TOKEN = os.getenv('DISCORD_TOKEN')
CODEX_TOKEN = os.getenv('CODEX_BOT_TOKEN')
FORUM_CHANNEL_ID = 1432625860917198928  # claudeとcodexの部屋

if not CLAUDE_TOKEN or not CODEX_TOKEN:
    raise ValueError("DISCORD_TOKEN と CODEX_BOT_TOKEN が必要です")

async def create_thread(title: str, content: str):
    """スレッドを作成してIDを返す"""
    client = discord.Client(intents=discord.Intents.default())
    thread_id = None

    @client.event
    async def on_ready():
        nonlocal thread_id
        try:
            forum_channel = await client.fetch_channel(FORUM_CHANNEL_ID)

            if isinstance(forum_channel, discord.ForumChannel):
                thread_with_message = await forum_channel.create_thread(
                    name=title,
                    content=content
                )
                thread_id = thread_with_message.thread.id
                print(f"THREAD_ID:{thread_id}")  # スレッドIDを出力
            else:
                print("ERROR:Not a forum channel", file=sys.stderr)
        except Exception as e:
            print(f"ERROR:{e}", file=sys.stderr)
        finally:
            await client.close()

    await client.start(CLAUDE_TOKEN)
    return thread_id

async def post_message(bot_type: str, thread_id: int, content: str):
    """メッセージを投稿"""
    token = CLAUDE_TOKEN if bot_type == "claude" else CODEX_TOKEN
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            thread = await client.fetch_channel(thread_id)
            await thread.send(content)
            print(f"SUCCESS:Message posted by {bot_type}")
        except Exception as e:
            print(f"ERROR:{e}", file=sys.stderr)
        finally:
            await client.close()

    await client.start(token)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    # 標準入力からメッセージを読み取る
    content = sys.stdin.read().strip()

    if not content:
        print("ERROR: No content provided via stdin", file=sys.stderr)
        sys.exit(1)

    if action == "create_thread":
        if len(sys.argv) != 3:
            print("Usage: echo 'content' | post_debate_realtime.py create_thread <title>")
            sys.exit(1)
        title = sys.argv[2]
        asyncio.run(create_thread(title, content))

    elif action in ["post_claude", "post_codex"]:
        if len(sys.argv) != 3:
            print(f"Usage: echo 'content' | post_debate_realtime.py {action} <thread_id>")
            sys.exit(1)
        thread_id = int(sys.argv[2])
        bot_type = "claude" if action == "post_claude" else "codex"
        asyncio.run(post_message(bot_type, thread_id, content))

    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
