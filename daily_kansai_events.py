#!/usr/bin/env python3
"""
毎日12時に関西地区の最新イベントを検索してDiscordフォーラムに投稿
"""
import os
import sys
import discord
import asyncio
from datetime import datetime
import subprocess
import json

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
EVENT_FORUM_ID = 1434499089420128317  # 🎪イベント

def search_kansai_events():
    """Gemini経由で関西地区のイベントを検索"""
    try:
        print('📋 関西地区のイベントを検索中...')

        # zshでask_gemini関数を実行
        query = '関西地区（大阪、京都、兵庫、奈良、滋賀、和歌山）の今月・来月の注目イベントを5つ教えてください。各イベントについて、タイトル、開催日時、場所、概要、公式URLを含めてください。JSON形式で返してください: [{"title": "", "date": "", "location": "", "description": "", "url": ""}]'

        command = f'source ~/.zshrc && ask_gemini "{query}"'

        result = subprocess.run(
            ['/bin/zsh', '-c', command],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            # JSON部分を抽出
            output = result.stdout.strip()

            # JSONブロックを探す
            if '```json' in output:
                json_start = output.find('```json') + 7
                json_end = output.find('```', json_start)
                json_str = output[json_start:json_end].strip()
            elif '[' in output and ']' in output:
                json_start = output.find('[')
                json_end = output.rfind(']') + 1
                json_str = output[json_start:json_end]
            else:
                print('❌ JSON形式のデータが見つかりません')
                return []

            try:
                events = json.loads(json_str)
                print(f'✅ {len(events)}件のイベントを取得')
                return events
            except json.JSONDecodeError as e:
                print(f'❌ JSON解析エラー: {e}')
                print(f'取得したデータ: {json_str[:500]}')
                return []
        else:
            print(f'❌ Gemini検索エラー: {result.stderr}')
            return []

    except Exception as e:
        print(f'❌ イベント検索エラー: {e}')
        import traceback
        traceback.print_exc()
        return []

def format_event_post(event):
    """イベント情報をDiscord投稿用にフォーマット"""
    title = event.get('title', '（タイトル不明）')
    date = event.get('date', '日時未定')
    location = event.get('location', '場所未定')
    description = event.get('description', '')
    url = event.get('url', '')

    content = f"""**📅 開催日時**
{date}

**📍 場所**
{location}

**📝 概要**
{description}
"""

    if url:
        content += f"\n**🔗 公式サイト**\n{url}"

    content += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n*自動投稿 | {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

    return title, content

async def main():
    """メイン処理"""
    print(f'🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - 関西イベント投稿開始')

    # イベント検索
    events = search_kansai_events()

    if not events:
        print('⚠️ 投稿するイベントがありません')
        return

    # Discord Bot起動
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'✅ Discord Bot起動: {client.user}')

        # フォーラムチャンネルを取得
        forum = client.get_channel(EVENT_FORUM_ID)
        if not forum:
            print(f'❌ フォーラムが見つかりません: {EVENT_FORUM_ID}')
            await client.close()
            return

        # 各イベントをスレッドとして投稿
        for i, event in enumerate(events, 1):
            try:
                title, content = format_event_post(event)

                # フォーラムにスレッドを作成
                thread = await forum.create_thread(
                    name=title[:100],  # タイトルは100文字まで
                    content=content
                )

                print(f'✅ イベント投稿成功 ({i}/{len(events)}): {title}')

                # レート制限対策
                await asyncio.sleep(2)

            except Exception as e:
                print(f'❌ イベント投稿エラー ({i}/{len(events)}): {e}')

        print(f'✅ 関西イベント投稿完了: {len(events)}件')
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
