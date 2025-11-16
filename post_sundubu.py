#!/usr/bin/env python3
import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKENが.envファイルに設定されていません。")

# Discord bot のインスタンス作成
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

FORUM_ID = 1433053243667251270  # 料理フォーラム
THREAD_TITLE = "スンドゥブ（純豆腐チゲ）"
THREAD_CONTENT = """## 材料（2人分）

**メイン材料:**
- 絹ごし豆腐 1丁（300g）
- あさり 200g（または冷凍シーフードミックス）
- 豚バラ肉 100g
- 玉ねぎ 1/2個
- ニラ 1/2束
- えのき 1/2袋
- 卵 2個

**スープ:**
- 水 500ml
- 鶏ガラスープの素 小さじ2
- 粉唐辛子（韓国産） 大さじ2
- コチュジャン 大さじ1
- 醤油 大さじ1
- にんにく（すりおろし） 1片分
- ごま油 大さじ1

## 作り方

1. あさりは砂抜きしておく
2. 豚バラ肉、玉ねぎは食べやすい大きさに切る
3. 鍋にごま油を熱し、豚肉と玉ねぎを炒める
4. 水、鶏ガラスープの素、調味料を全て加えて煮立たせる
5. あさり、えのきを加えて蓋をし、あさりが開くまで煮る
6. 豆腐をスプーンですくって加え、ニラを入れる
7. 卵を割り入れて火を止める

## メモ
- 辛さは粉唐辛子の量で調整
- 土鍋や石焼鍋で作ると雰囲気が出る
- ご飯と一緒に食べるのがおすすめ"""

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        forum_channel = bot.get_channel(FORUM_ID)
        if not forum_channel:
            print(f"❌ フォーラムID {FORUM_ID} が見つかりません")
            await bot.close()
            return

        if not isinstance(forum_channel, discord.ForumChannel):
            print(f"❌ ID {FORUM_ID} はフォーラムチャンネルではありません")
            await bot.close()
            return

        print(f"💬 フォーラム: {forum_channel.name}")

        # フォーラムに新しいスレッドを作成
        thread_with_message = await forum_channel.create_thread(
            name=THREAD_TITLE,
            content=THREAD_CONTENT
        )

        thread = thread_with_message.thread

        print(f"✅ スレッドを作成しました")
        print(f"   タイトル: {THREAD_TITLE}")
        print(f"   スレッドID: {thread.id}")
        print(f"   URL: https://discord.com/channels/{forum_channel.guild.id}/{thread.id}")

    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
