#!/usr/bin/env python3
"""
Bambu Lab A1フォーラムスレッドにv4.0設計図をアップロード
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
            discord.File(f"{base_dir}/design_diagram_v4.png", filename="設計図_v4.0_収束型傾斜.png"),
            discord.File(f"{base_dir}/convergence_concept.png", filename="収束型傾斜_概念図.png"),
        ]

        message_content = """📎 **v4.0 収束型傾斜 + 排出口設計** 🎯

**新機能:**
✅ **収束型底面** - すべての方向から1点に集まる
✅ **排出口Ø50mm** - 前端中央、完全貫通の穴
✅ **V字型底面** - 幅方向も20度傾斜
✅ **ピラミッド型** - 立体的な傾斜構造

**傾斜角度:**
• 前後方向: 30度（高低差90mm）
• 幅方向: 20度（V字型）

**ファイル一式:**
1. **設計図_v4.0_収束型傾斜.png** - 詳細設計図（9面図）
2. **収束型傾斜_概念図.png** - わかりやすい概念図

**注意:**
⚠️ 構造が複雑化（印刷時間+4時間、合計22時間）
⚠️ STL生成の実装が必要（2-3時間）
⚠️ メッシュ数が大幅増加

**次のステップ:**
実装の承認を待っています。問題なければSTL生成を開始します！"""

        try:
            # ファイルをアップロード
            await thread.send(content=message_content, files=files)
            print("✅ v4.0設計図をアップロードしました")
        except Exception as e:
            print(f"❌ エラー: {e}")

        await client.close()

    await client.start(TOKEN)

# 実行
if __name__ == "__main__":
    asyncio.run(upload_to_thread())
