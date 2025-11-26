#!/usr/bin/env python3
"""
Bambu Lab A1フォーラムにSTLファイルと設計図をアップロード
"""
import discord
import os
import asyncio

# フォーラムチャンネルID
FORUM_CHANNEL_ID = 1443097746251841697

async def upload_to_forum():
    # Discordボットトークン
    token_file = os.path.expanduser("~/.discord_bot_token")
    with open(token_file, "r") as f:
        TOKEN = f.read().strip()

    # Intents設定
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}")

        # フォーラムチャンネルを取得
        forum = client.get_channel(FORUM_CHANNEL_ID)
        if not forum:
            print(f"❌ フォーラムチャンネル {FORUM_CHANNEL_ID} が見つかりません")
            await client.close()
            return

        print(f"✅ フォーラム '{forum.name}' を取得しました")

        # スレッドを作成
        thread_name = "コインシュート設計 v3.0 (ULTRATHINK最適化)"
        thread_content = """## 🛠️ コインシュート設計完了（v3.0 - ULTRATHINK最適化版）

**📐 設計仕様:**
- 外寸: 240mm × 315mm × 120mm
- 前後2分割: Back 220mm + Front 105mm
- **組立後サイズ: 正確に315mm** （220 + 105 - 10mm重なり）
- **壁厚: 4mm** （コイン重量に耐える強度）
- 内側傾斜: 20度（高低差114.7mm）
- 前壁: 30mm高さ（上部90mm開放）
- 接合: PETGスナップフィット（0.3mmクリアランス）

**✅ 主要改善点:**
1. 壁厚 2mm → 4mm：コイン重量に十分耐える
2. サイズ正確化：Back 220mm + Front 105mm = 315mm
3. 前壁強化：10mm → 30mm（構造強度向上）
4. 組立後サイズ保証：ジョイント10mm重なりを考慮

**📦 生成ファイル:**
- coin_chute_back.stl (220mm、入口側)
- coin_chute_front.stl (105mm、出口側)
- DESIGN_SPEC.md (詳細設計仕様書)
- generate_stl_front_back.py (生成スクリプト)

**🖨️ 印刷推奨設定:**
- 材質: PETG
- 壁数: 9壁（≈4mm）
- インフィル: 20%
- レイヤー高: 0.2mm
- ノズル温度: 230-240°C
- ベッド温度: 70-80°C
- ブリム: 推奨

**📊 印刷時間・材料:**
- Back: 約12時間、300g
- Front: 約6時間、150g
- **合計: 約18時間、450g**

詳細は添付の設計図とDESIGN_SPEC.mdを参照してください。"""

        # ファイルパス
        base_dir = "/Users/minamitakeshi/3d_models/coin_chute"
        files = [
            discord.File(f"{base_dir}/design_diagram_v3.png", filename="設計図_v3.0.png"),
            discord.File(f"{base_dir}/coin_chute_back.stl", filename="coin_chute_back.stl"),
            discord.File(f"{base_dir}/coin_chute_front.stl", filename="coin_chute_front.stl"),
            discord.File(f"{base_dir}/DESIGN_SPEC.md", filename="DESIGN_SPEC.md"),
        ]

        try:
            # スレッドを作成してファイルアップロード
            thread = await forum.create_thread(
                name=thread_name,
                content=thread_content,
                files=files
            )
            print(f"✅ スレッドを作成しました: {thread.thread.name}")
            print(f"   URL: https://discord.com/channels/{forum.guild.id}/{thread.thread.id}")
        except Exception as e:
            print(f"❌ エラー: {e}")

        await client.close()

    await client.start(TOKEN)

# 実行
asyncio.run(upload_to_forum())
