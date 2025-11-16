import os
import discord
from dotenv import load_dotenv
import asyncio

# .envファイルから環境変数を読み込む
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKENが.envファイルに設定されていません。")

# Discord bot のインスタンス作成
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

MIDJOURNEY_CHANNEL_ID = 1432180180985708648  # #midjourney チャンネル

@client.event
async def on_ready():
    print(f'✅ Bot logged in as {client.user}\n')

    try:
        channel = client.get_channel(MIDJOURNEY_CHANNEL_ID)
        if not channel:
            print(f"❌ チャンネルID {MIDJOURNEY_CHANNEL_ID} が見つかりません")
            await client.close()
            return

        print(f"📝 チャンネル: #{channel.name}")
        print(f"   ID: {channel.id}")
        print(f"   カテゴリ: {channel.category.name if channel.category else 'なし'}\n")
        print("=" * 80)
        print("最新20件のメッセージ履歴:")
        print("=" * 80 + "\n")

        # 最新20件のメッセージを取得
        messages = []
        async for message in channel.history(limit=20):
            messages.append(message)

        # 古い順に並べ替え
        messages.reverse()

        for msg in messages:
            author_name = f"{msg.author.name}"
            if msg.author.bot:
                author_name += " [BOT]"

            print(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {author_name}:")
            print(f"  {msg.content[:200]}")  # 最初の200文字のみ表示

            # 添付ファイルがあれば表示
            if msg.attachments:
                print(f"  📎 添付ファイル: {len(msg.attachments)}件")
                for att in msg.attachments:
                    print(f"     - {att.filename}")

            # Embedがあれば表示
            if msg.embeds:
                print(f"  🖼️  Embed: {len(msg.embeds)}件")

            print()

        print("=" * 80)
        print("履歴取得完了")
        print("=" * 80)

    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        await client.close()

# Botを起動
client.run(TOKEN)
