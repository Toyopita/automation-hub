#!/usr/bin/env python3
"""
出雲組の料理フォーラムからMinamiサーバーの料理フォーラムにスンドゥブのスレッドを移植
"""

import asyncio
import os
from dotenv import load_dotenv
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MINAMI_COOKING_FORUM_ID = 1433974530971402270  # Minamiサーバーの料理フォーラム

if not TOKEN:
    raise ValueError("DISCORD_TOKEN が必要です")

async def create_sundubu_thread():
    """スンドゥブスレッドを作成"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            forum_channel = await client.fetch_channel(MINAMI_COOKING_FORUM_ID)

            if isinstance(forum_channel, discord.ForumChannel):
                # スレッド作成（最初のメッセージ）
                content = """## 材料（2人分）

**メイン材料:**
- 絹ごし豆腐 1丁（300g）
- 豚バラ肉 100g
- 白菜 1/4個
- 玉ねぎ 1/2個
- ニラ 1/2束
- えのき 1/2袋
- 舞茸 1/2パック
- 卵 2個

**スープ:**
- スンドゥブの素 1袋
- 水 適量（パッケージの指示に従う）

## 作り方

1. 豚バラ肉、白菜、玉ねぎは食べやすい大きさに切る
2. 鍋で豚肉と玉ねぎを炒める
3. 水とスンドゥブの素を加えて煮立たせる
4. 白菜、えのき、舞茸を加えて煮る
5. 豆腐をスプーンですくって加え、ニラを入れる
6. 卵を割り入れて火を止める

## メモ
- スンドゥブの素で簡単に本格的な味が楽しめます
- 土鍋や石焼鍋で作ると雰囲気が出る
- ご飯と一緒に食べるのがおすすめ"""

                thread_with_message = await forum_channel.create_thread(
                    name="スンドゥブ（純豆腐チゲ）",
                    content=content
                )

                thread = thread_with_message.thread
                print(f"✅ スレッド作成完了: {thread.name} (ID: {thread.id})")
                print(f"✅ Minamiサーバーの料理フォーラムにスンドゥブのレシピを移植しました")

            else:
                print("ERROR: 指定されたチャンネルはフォーラムではありません")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await client.close()

    await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(create_sundubu_thread())
