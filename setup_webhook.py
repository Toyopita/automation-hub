#!/usr/bin/env python3
"""
Discord Webhookをセットアップするスクリプト
既存のWebhookがあればそれを使い、なければ新規作成する
"""
import discord
import os
import sys

# .envファイルから読み込み
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        print("❌ .envファイルが見つかりません")
        sys.exit(1)
    return env_vars

env = load_env_file()
TOKEN = env.get('DISCORD_TOKEN')
CHANNEL_ID = 1434368052916392076

if not TOKEN:
    print("❌ DISCORD_TOKENが設定されていません")
    sys.exit(1)

intents = discord.Intents.default()
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    try:
        print(f'✅ ログイン成功: {client.user}')

        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            print(f'❌ チャンネルが見つかりません: {CHANNEL_ID}')
            await client.close()
            return

        print(f'✅ チャンネル取得成功: {channel.name}')

        # 既存のWebhookを取得
        webhooks = await channel.webhooks()
        webhook_url = None

        # 既存のWebhookから探す
        for wh in webhooks:
            if wh.name == '今日の予定 自動投稿':
                webhook_url = wh.url
                print(f'✅ 既存のWebhookを使用します: {wh.name}')
                break

        # 既存のWebhookがなければ作成
        if not webhook_url:
            print('📝 新しいWebhookを作成します...')
            new_webhook = await channel.create_webhook(name='今日の予定 自動投稿')
            webhook_url = new_webhook.url
            print(f'✅ Webhook作成成功')

        # Webhook URLを表示
        print(f'\n━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'Webhook URL:')
        print(f'{webhook_url}')
        print(f'━━━━━━━━━━━━━━━━━━━━━━━━\n')

        # .envファイルに保存（既にあればスキップ）
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if 'DISCORD_WEBHOOK_URL' not in env:
            with open(env_path, 'a') as f:
                f.write(f'\nDISCORD_WEBHOOK_URL={webhook_url}\n')
            print('✅ .envファイルに保存しました')
        else:
            print('ℹ️  .envファイルには既に設定されています')

    except Exception as e:
        print(f'❌ エラーが発生しました: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

# 実行
try:
    client.run(TOKEN)
except KeyboardInterrupt:
    print('\n中断されました')
except Exception as e:
    print(f'❌ 実行エラー: {e}')
    import traceback
    traceback.print_exc()
