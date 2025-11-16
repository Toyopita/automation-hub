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

THREAD_ID = 1433061565040689257  # スンドゥブスレッド
NEW_CONTENT = """## 材料（2人分）

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

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

    try:
        thread = bot.get_channel(THREAD_ID)
        if not thread:
            print(f"❌ スレッドID {THREAD_ID} が見つかりません")
            await bot.close()
            return

        if not isinstance(thread, discord.Thread):
            print(f"❌ ID {THREAD_ID} はスレッドではありません")
            await bot.close()
            return

        print(f"💬 スレッド: {thread.name}")

        # スレッドの最初のメッセージを取得
        starter_message = thread.starter_message
        if not starter_message:
            # starter_messageがキャッシュされていない場合は取得
            starter_message = await thread.fetch_message(thread.id)

        print(f"📝 メッセージを編集中...")

        # メッセージを編集
        await starter_message.edit(content=NEW_CONTENT)

        print(f"✅ メッセージを更新しました")
        print(f"   変更内容: スンドゥブの素を使用するレシピに変更")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.close()

# Botを起動
bot.run(TOKEN)
