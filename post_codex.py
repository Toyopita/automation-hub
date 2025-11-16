#!/usr/bin/env python3
"""
Codexの発言をDiscordフォーラムスレッドに投稿するスクリプト
Usage: python post_codex.py <thread_id> <message>
"""

import discord
import asyncio
import os
import sys

def load_env():
    """環境変数を.envファイルから読み込む"""
    env_file = os.path.expanduser('~/discord-mcp-server/.env')
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

async def post_message(thread_id: int, message: str):
    """Discordスレッドにメッセージを投稿"""
    load_env()
    CODEX_TOKEN = os.getenv('CODEX_BOT_TOKEN')

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'{client.user} としてログインしました')

        thread = client.get_channel(thread_id)

        if not thread:
            print(f"エラー: スレッドID {thread_id} が見つかりませんでした")
            await client.close()
            return

        await thread.send(message)
        print(f"メッセージを投稿しました: {message[:50]}...")

        await asyncio.sleep(1)
        await client.close()

    await client.start(CODEX_TOKEN)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python post_codex.py <thread_id> <message>")
        sys.exit(1)

    thread_id = int(sys.argv[1])
    message = sys.argv[2]

    asyncio.run(post_message(thread_id, message))
