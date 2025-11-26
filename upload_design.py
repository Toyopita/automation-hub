#!/usr/bin/env python3
"""
Bambu Lab A1フォーラムスレッドに設計図をアップロード
"""
import discord
import os
import asyncio

# スレッドID
THREAD_ID = 1443181273483972618

# スクリプトのディレクトリ
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# .envファイルから環境変数を読み込み
def load_env_file():
    env_path = os.path.join(SCRIPT_DIR, '.env')
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

env = load_env_file()
TOKEN = env.get('DISCORD_TOKEN')

async def upload_to_thread():
    # Intents設定
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}")

        # スレッドを取得
        thread = client.get_channel(THREAD_ID)
        if not thread:
            print(f"❌ スレッド {THREAD_ID} が見つかりません")
            await client.close()
            return

        print(f"✅ スレッド '{thread.name}' を取得しました")

        # ファイルパス
        base_dir = "/Users/minamitakeshi/3d_models/coin_chute"
        files = [
            discord.File(f"{base_dir}/design_diagram_v3.png", filename="設計図_v3.1_コイン流出改善版.png"),
            discord.File(f"{base_dir}/coin_chute_back.stl", filename="coin_chute_back_v3.1.stl"),
            discord.File(f"{base_dir}/coin_chute_front.stl", filename="coin_chute_front_v3.1.stl"),
        ]

        message_content = """📎 **v3.1 アップデート - コイン流出改善版** 🚀

**主要改善点:**
✅ 傾斜角度: **20° → 30°** (+10°、より強い流れ)
✅ 前壁高さ: **30mm → 15mm** (上部開放 90mm → 105mm)
✅ 高低差: **114.7mm → 181.9mm** (+67.2mm、大幅改善)

**ファイル一式:**
1. **設計図_v3.1_コイン流出改善版.png** - 全体設計図（30°傾斜対応）
2. **coin_chute_back_v3.1.stl** - Backパーツ（220mm、30°傾斜、約300g）
3. **coin_chute_front_v3.1.stl** - Frontパーツ（105mm、15mm前壁、約150g）

**印刷可能な状態です！** 🎉
コインがより前方までスムーズに流れる設計になりました。"""

        try:
            # ファイルをアップロード
            await thread.send(content=message_content, files=files)
            print("✅ ファイルをアップロードしました")
        except Exception as e:
            print(f"❌ エラー: {e}")

        await client.close()

    await client.start(TOKEN)

# 実行
if __name__ == "__main__":
    asyncio.run(upload_to_thread())
