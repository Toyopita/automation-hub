#!/usr/bin/env python3
"""
channels.py を使った使用例

このスクリプトは、channels.py で定義された定数を使って
チャンネルやフォーラムにアクセスする方法を示します。
"""

import asyncio
import os
from dotenv import load_dotenv
import discord

# channels.py から定数をインポート
from channels import CHANNELS, FORUMS, CATEGORIES

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

async def example_usage():
    """使用例"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        print("=== channels.py 使用例 ===\n")

        # 例1: テキストチャンネルにアクセス
        print("【例1】テキストチャンネルにアクセス")
        rule_channel_id = CHANNELS["ルール"]
        print(f"  ルールチャンネルID: {rule_channel_id}")

        rule_channel = await client.fetch_channel(rule_channel_id)
        print(f"  チャンネル名: {rule_channel.name}\n")

        # 例2: フォーラムチャンネルにアクセス
        print("【例2】フォーラムチャンネルにアクセス")
        forum_id = FORUMS["朝刊太郎のチュートリアル"]
        print(f"  朝刊太郎のチュートリアルID: {forum_id}")

        forum = await client.fetch_channel(forum_id)
        print(f"  フォーラム名: {forum.name}")
        print(f"  スレッド数: {len(forum.threads)}\n")

        # 例3: 複数のチャンネルを一度に確認
        print("【例3】よく使うチャンネル一覧")
        important_channels = ["ルール", "お知らせ", "システム通知"]
        for ch_name in important_channels:
            ch_id = CHANNELS.get(ch_name)
            if ch_id:
                channel = await client.fetch_channel(ch_id)
                print(f"  {ch_name}: {channel.name} (ID: {ch_id})")

        print("\n=== 完了 ===")
        await client.close()

    await client.start(TOKEN)

if __name__ == "__main__":
    print("""
channels.py の使い方:
--------------------
1. スクリプト内でインポート:
   from channels import CHANNELS, FORUMS

2. チャンネルIDを取得:
   channel_id = CHANNELS["ルール"]
   forum_id = FORUMS["朝刊太郎のチュートリアル"]

3. 利用可能な定数:
   - CHANNELS: テキストチャンネル
   - FORUMS: フォーラムチャンネル
   - CATEGORIES: カテゴリ

4. channels.pyの更新:
   python generate_channels_config.py
--------------------
""")

    asyncio.run(example_usage())
