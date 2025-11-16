#!/usr/bin/env python3
import discord
import os
import asyncio

# .envファイルから直接読み込み
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
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
CHANNEL_ID = 1434368052916392076

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    channel = client.get_channel(CHANNEL_ID)
    if channel:
        # Webhookを作成
        webhook = await channel.create_webhook(name='今日の予定 自動投稿')
        print(f'✅ Webhook作成成功')
        print(f'Webhook URL: {webhook.url}')

        # .envファイルに自動保存
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        with open(env_path, 'a') as f:
            f.write(f'\nDISCORD_WEBHOOK_URL={webhook.url}\n')
        print(f'✅ .envファイルに保存しました')
    else:
        print(f'❌ チャンネルが見つかりません')

    await client.close()

asyncio.run(client.start(TOKEN))
