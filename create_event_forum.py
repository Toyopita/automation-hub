#!/usr/bin/env python3
"""
プライベートカテゴリに「イベント」フォーラムチャンネルを作成
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
PRIVATE_CATEGORY_ID = 1434324454967742564  # ━━━ プライベート ━━━

async def main():
    """メイン処理"""
    print('🔧 イベントフォーラムを作成中...')

    intents = discord.Intents.default()
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        # カテゴリを取得
        category = client.get_channel(PRIVATE_CATEGORY_ID)
        if not category:
            print(f'❌ カテゴリが見つかりません: {PRIVATE_CATEGORY_ID}')
            await client.close()
            return

        # 既存のイベントフォーラムを確認
        for channel in category.channels:
            if channel.name == '🎪イベント' and isinstance(channel, discord.ForumChannel):
                print(f'✅ 既存のイベントフォーラムが見つかりました: {channel.id}')
                await client.close()
                return

        # フォーラムチャンネルを作成
        try:
            forum = await category.create_forum(
                name='🎪イベント',
                topic='関西地区の最新イベント情報',
                position=0
            )
            print(f'✅ イベントフォーラム作成成功: {forum.id}')
        except Exception as e:
            print(f'❌ フォーラム作成エラー: {e}')

        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
