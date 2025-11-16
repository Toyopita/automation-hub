#!/usr/bin/env python3
"""
Discord自動化システムの現状をお知らせチャンネルに投稿
"""
import os
import discord
import asyncio
from datetime import datetime

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
ANNOUNCEMENT_CHANNEL_ID = 1430791442959433829  # 🔔｜お知らせ

def create_status_message():
    """自動化状況のメッセージを作成"""
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day

    message = f"""# 🤖 Discord自動化システム 稼働状況

**更新日時:** {year}年{month}月{day}日

━━━━━━━━━━━━━━━━━━━━━━━━

## ⏰ 定期自動投稿（6件）

### 📅 毎朝6:00実行
**📅｜今日の予定 & 📋｜タスク通知**
- Googleカレンダーの予定を自動投稿
  - 六曜カレンダー
  - 祖霊社
  - 本社
  - 年祭
  - 冥福祭
- Notionの締切間近タスクを自動投稿
  - 祖霊社タスクDB（1週間以内締切）

### 📋 毎晩20:00実行
**📋｜発注ログ**
- Notion発注履歴DBから当日の発注を自動投稿
  - 発注書名
  - 分類（野菜果物、鯛、餅、榊、乾物、白雪糕）
  - 発注書リンク

### 📰 その他定期投稿
- **AI関連ニュース**: 定期配信
- **Notion関連ニュース**: 定期配信
- **チャンネル自動アーカイブ**: 定期実行

━━━━━━━━━━━━━━━━━━━━━━━━

## 🔄 常時稼働Bot（5件）

### 📚 書籍管理Bot
フォーラム「書籍」で書籍情報を管理

### 📦 発注通知Bot
発注関連の通知を自動処理

### 🍶 酒在庫監視Bot
酒の在庫を監視・通知

### 🍚 米在庫監視Bot
米の在庫を監視・通知

### 📅 カレンダー監視Bot
カレンダーイベントをリアルタイム監視

━━━━━━━━━━━━━━━━━━━━━━━━

## 📋 データソース

### Notion
- **祖霊社タスクDB**: タスク管理
- **祖霊社プロジェクトDB**: プロジェクト管理
- **発注履歴DB**: 発注記録

### Google Calendar
- 複数カレンダーから予定を自動取得

━━━━━━━━━━━━━━━━━━━━━━━━

## ⚙️ システム要件

- **実行環境**: MacBook（`~/discord-mcp-server/`）
- **必要条件**: MacBookが起動している必要あり
- **ログ保存**: `~/discord-mcp-server/*.log`

━━━━━━━━━━━━━━━━━━━━━━━━

## 📞 問い合わせ

自動化システムに関する質問や要望は、Claudeに相談してください。

*このメッセージは自動投稿システムの説明です。*"""

    return message

async def main():
    """メイン処理"""
    print('📢 自動化状況を投稿中...')

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            message = create_status_message()
            await channel.send(message)
            print('✅ お知らせ投稿成功')
        else:
            print(f'❌ チャンネルが見つかりません: {ANNOUNCEMENT_CHANNEL_ID}')

        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
