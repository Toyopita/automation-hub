#!/usr/bin/env python3
"""
未処理伝承投稿をチェックして通知するスクリプト

定期実行（毎日21時）で未処理投稿があるか確認し、
あればDiscordチャンネルに通知します。
"""

import asyncio
import os
import json
from dotenv import load_dotenv
import discord

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TRADITION_CHANNEL_ID = 1438876441226903673  # 📖｜伝承投稿

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN が必要です")

async def check_and_notify():
    """未処理投稿をチェックして通知"""
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        try:
            channel = await client.fetch_channel(TRADITION_CHANNEL_ID)

            # 未処理メッセージを取得（✅リアクションがないもの）
            unprocessed_count = 0
            unprocessed_messages = []

            async for message in channel.history(limit=100):
                # Botのメッセージは除外
                if message.author.bot:
                    continue

                # ✅リアクションがあれば処理済み
                has_check = any(
                    reaction.emoji == '✅'
                    for reaction in message.reactions
                )

                if not has_check:
                    unprocessed_count += 1
                    unprocessed_messages.append({
                        'author': str(message.author),
                        'content': message.content[:50] + '...' if len(message.content) > 50 else message.content,
                        'url': message.jump_url
                    })

                    # 最大5件まで表示
                    if len(unprocessed_messages) >= 5:
                        break

            print(f'未処理投稿: {unprocessed_count}件')

            # 未処理投稿がある場合は通知
            if unprocessed_count > 0:
                message_list = '\n'.join([
                    f"• [{msg['author']}] {msg['content']}\n  {msg['url']}"
                    for msg in unprocessed_messages
                ])

                more_text = f"\n\n...他{unprocessed_count - len(unprocessed_messages)}件" if unprocessed_count > len(unprocessed_messages) else ""

                notification = (
                    f"📖 **未処理の伝承投稿が{unprocessed_count}件あります**\n\n"
                    f"{message_list}{more_text}\n\n"
                    f"Claude Codeに「**新しい伝承を確認して**」と指示すると、\n"
                    f"伝承を解析してNotion DBに登録できます。"
                )

                await channel.send(notification)
                print('✅ 通知を送信しました')
            else:
                print('未処理投稿はありません')

        except Exception as e:
            print(f'❌ エラー: {e}')
        finally:
            await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(check_and_notify())
