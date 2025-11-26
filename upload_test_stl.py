#!/usr/bin/env python3
"""
v4.0テスト版STLファイルをBambu Lab A1フォーラムにアップロード
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
            discord.File(f"{base_dir}/coin_chute_v41_test.stl",
                        filename="coin_chute_v41_test.stl"),
        ]

        message_content = """**v4.1（1/10スケール）**

📏 サイズ: 24×35×12mm
🕳️ 排出口: x=30mm (WALL_THICKNESS上)
🪝 フック: 4箇所

「下に小さな層」の問題を特定中。
スライサーのスクショで問題箇所を教えてください。"""

        try:
            # ファイルをアップロード
            await thread.send(content=message_content, files=files)
            print("✅ テスト版STLをアップロードしました")
        except Exception as e:
            print(f"❌ エラー: {e}")

        await client.close()

    await client.start(TOKEN)

# 実行
if __name__ == "__main__":
    asyncio.run(upload_to_thread())
