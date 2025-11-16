#!/usr/bin/env python3
"""
献酒・献米チャンネルに投稿フォーマット例を投稿
"""
import os
import discord
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

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
DISCORD_TOKEN = env.get('DISCORD_TOKEN')
SAKE_CHANNEL_ID = 1430362136726605876  # 🍶｜献酒
RICE_CHANNEL_ID = 1434159642912751696  # 🌾｜献米

SAKE_FORMAT = """# 🍶 献酒の投稿フォーマット

このチャンネルに献酒情報を投稿すると、**自動的にNotionデータベースに登録**されます。

## ✅ 正しい投稿例

```
2025年1月 本部
賀茂鶴 1000
樽酒 500
上撰 300
```

```
2025年2月 祖霊社
賀茂鶴 800
飛翔 200
典雅 150
その他 100
```

## 📋 記載項目

1. **年月**: `2025年1月` の形式で記載
2. **部署**: `本部` または `祖霊社`
3. **献酒の種類と数量**:
   - 賀茂鶴
   - 樽酒
   - 上撰
   - 飛翔
   - 典雅
   - その他

## ⚠️ 注意点

- 数量は半角数字で記載してください
- 種類名の後に数量を記載してください
- 0より大きい数量のみ登録されます

━━━━━━━━━━━━━━━━━━━━━━━━

*このメッセージは献酒管理システムの説明です*
*質問があればClaudeに相談してください*"""

RICE_FORMAT = """# 🌾 献米の投稿フォーマット

このチャンネルに献米情報を投稿すると、**自動的にNotionデータベースに登録**されます。

## ✅ 正しい投稿例

```
2025年10月 本部
黒30、20
白30、1
モチ30、1
黒10、3
黒15、2
黒5、1
```

```
2025年11月 祖霊社
白20、5
黒15、3
モチ10、2
```

## 📋 記載項目

1. **年月**: `2025年1月` の形式で記載
2. **部署**: `本部` または `祖霊社`
3. **献米の種類、重量（kg）、袋数**:
   - 白
   - 黒
   - モチ
   - その他

**フォーマット**: `種類キロ数、袋数`
- 例: `白30、1` = 白30キロが1袋 → 合計30kg
- 例: `黒15、2` = 黒15キロが2袋 → 合計30kg
- 例: `黒10、3` = 黒10キロが3袋 → 合計30kg

## ⚠️ 注意点

- 数量は半角数字で記載してください
- **順番**: キロ数、袋数の順で記載
- 同じ種類でも袋のサイズが違う場合は、別の行に記載してください
- キロ数と袋数の間は「、」（全角カンマ）または「,」（半角カンマ）で区切ってください
- 0より大きい数量のみ登録されます

━━━━━━━━━━━━━━━━━━━━━━━━

*このメッセージは献米管理システムの説明です*
*質問があればClaudeに相談してください*"""

async def main():
    """メイン処理"""
    print('📋 フォーマット例を投稿中...')

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        # 献酒チャンネルに投稿
        sake_channel = client.get_channel(SAKE_CHANNEL_ID)
        if sake_channel:
            await sake_channel.send(SAKE_FORMAT)
            print('✅ 献酒フォーマット投稿成功')
        else:
            print(f'❌ 献酒チャンネルが見つかりません: {SAKE_CHANNEL_ID}')

        # 献米チャンネルに投稿
        rice_channel = client.get_channel(RICE_CHANNEL_ID)
        if rice_channel:
            await rice_channel.send(RICE_FORMAT)
            print('✅ 献米フォーマット投稿成功')
        else:
            print(f'❌ 献米チャンネルが見つかりません: {RICE_CHANNEL_ID}')

        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
