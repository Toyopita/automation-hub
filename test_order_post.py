#!/usr/bin/env python3
"""
テスト用: 最新の発注履歴1件をDiscordに投稿
"""
import os
import sys
import json
import discord
import asyncio
from datetime import datetime, timedelta
import subprocess

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

DISCORD_TOKEN = env.get('DISCORD_TOKEN')
ORDER_LOG_CHANNEL_ID = 1430362512225996840  # 📋｜発注ログ

def get_latest_order():
    """Node.jsスクリプト経由で最新の発注履歴1件を取得"""
    node_script = os.path.join(SCRIPT_DIR, 'get_latest_order.js')

    try:
        result = subprocess.run(
            ['node', node_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('orders', [])
        else:
            print(f'❌ 発注履歴取得エラー: {result.stderr}')
            return []
    except Exception as e:
        print(f'❌ 発注履歴取得エラー: {e}')
        import traceback
        traceback.print_exc()
        return []

def format_order_message(orders):
    """発注履歴メッセージをフォーマット"""
    today = datetime.now()
    year = today.year
    month = today.month
    day = today.day
    hour = today.hour
    minute = today.minute

    if not orders:
        return "❌ 発注履歴が見つかりませんでした"

    orders_section = ''
    for order in orders:
        name = order.get('name', '（タイトルなし）')
        url = order.get('url', '')
        category = order.get('category', '')
        created_time = order.get('created_time', '')

        # カテゴリの絵文字
        category_emoji = {
            '野菜果物': '🥬',
            '鯛': '🐟',
            '餅': '🍡',
            '榊': '🌿',
            '乾物': '🍚',
            '白雪糕': '🍰'
        }.get(category, '📦')

        # 時刻を抽出（HH:MM形式）
        time_str = ''
        if created_time:
            try:
                dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                # JSTに変換（UTC+9）
                dt_jst = dt + timedelta(hours=9)
                time_str = dt_jst.strftime('%Y-%m-%d %H:%M')
            except:
                pass

        if category:
            orders_section += f'{category_emoji} **{name}** ({category})\n'
        else:
            orders_section += f'📦 **{name}**\n'

        if time_str:
            orders_section += f'`発注日時: {time_str}`\n'

        if url:
            orders_section += f'[発注書を開く]({url})\n'

        orders_section += '\n'

    message = f"""📋 **【テスト投稿】最新の発注履歴**

━━━━━━━━━━━━━━━━━━━━━━━━

{orders_section}━━━━━━━━━━━━━━━━━━━━━━━━
`テスト投稿 | {year}-{str(month).zfill(2)}-{str(day).zfill(2)} {str(hour).zfill(2)}:{str(minute).zfill(2)}`"""

    return message

async def main():
    """メイン処理"""
    print(f'🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - テスト投稿開始')

    # 最新の発注履歴取得
    print('📋 最新の発注履歴を取得中...')
    orders = get_latest_order()
    print(f'   {len(orders)}件の発注を取得')

    # Discord Bot起動
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        # 発注履歴を投稿
        order_channel = client.get_channel(ORDER_LOG_CHANNEL_ID)
        if order_channel:
            print('📋 発注履歴を投稿中...')
            order_message = format_order_message(orders)
            await order_channel.send(order_message)
            print('✅ 発注履歴投稿成功')
        else:
            print(f'❌ チャンネルが見つかりません: {ORDER_LOG_CHANNEL_ID}')

        print('✅ テスト投稿完了')
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
