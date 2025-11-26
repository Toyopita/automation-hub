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
            discord.File(f"{base_dir}/coin_chute_v4_test_1_10.stl",
                        filename="coin_chute_v4_test_1_10.stl"),
            discord.File(f"{base_dir}/v4_test_bambu_settings.txt",
                        filename="Bambu_Studio印刷設定.txt"),
        ]

        message_content = """🎯 **v4.0 テスト版（1/10スケール）** 🔬

**すぐ印刷できます！**

📏 **サイズ**: 24×31.5×12mm（超小型）
⏱️ **印刷時間**: 約10-15分
💰 **材料**: 約5-10g
🎨 **材質**: PETG推奨（PLAでもOK）

**ファイル:**
1. `coin_chute_v4_test_1_10.stl` - 印刷用STLファイル
2. `Bambu_Studio印刷設定.txt` - 詳細な推奨設定

**特徴:**
✅ 収束型ピラミッド底面
✅ 排出口Ø5mm（中央）
✅ 前後30度+幅20度の傾斜
✅ サポート不要

**Bambu Studioでの開き方:**
1. STLファイルをインポート
2. PETG、2壁、20%インフィル
3. ブリム推奨（反り防止）
4. スライス → 印刷開始！

**このテストの目的:**
構造確認後、フルサイズ（240×315×120mm）を実装します 🚀"""

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
