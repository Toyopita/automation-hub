#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord 既存チャンネルをフォーラムスレッドに移行
"""

import os
import discord
import asyncio

TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
    with open('.env') as f:
        for line in f:
            if line.startswith('DISCORD_TOKEN='):
                TOKEN = line.strip().split('=', 1)[1]

IZUMO_GUILD_ID = 1430359607905222658

# 移行対象チャンネル（チャンネル名で検索）
MIGRATION_TARGETS = [
    {
        'channel_name': '🪦｜秋季神霊大祭_2025',
        'forum_name': '📋-秋季神霊大祭',
        'thread_title': '2025_秋季神霊大祭'
    },
    {
        'channel_name': '🌅｜神迎祭_2025',
        'forum_name': '📋-神迎祭',
        'thread_title': '2025_神迎祭'
    }
]

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'✅ Bot接続成功: {client.user.name}')

    guild = client.get_guild(IZUMO_GUILD_ID)
    if not guild:
        print(f'❌ IZUMOサーバーが見つかりません')
        await client.close()
        return

    print(f'📁 サーバー: {guild.name}\n')

    for target in MIGRATION_TARGETS:
        print(f'🔄 {target["channel_name"]} → {target["forum_name"]} に移行開始...')

        # 元チャンネルを取得
        source_channel = discord.utils.get(guild.text_channels, name=target['channel_name'])
        if not source_channel:
            print(f'  ❌ チャンネル {target["channel_name"]} が見つかりません')
            continue

        print(f'  ✅ 元チャンネル確認: {source_channel.name} (ID: {source_channel.id})')

        # フォーラムチャンネルを取得
        forum_channel = discord.utils.get(guild.channels, name=target['forum_name'])
        if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
            print(f'  ❌ フォーラム {target["forum_name"]} が見つかりません')
            continue

        print(f'  ✅ フォーラム確認: {forum_channel.name} (ID: {forum_channel.id})')

        # メッセージ履歴を取得（古い順）
        messages = []
        print(f'  📥 メッセージ履歴を取得中...')
        async for message in source_channel.history(limit=None, oldest_first=True):
            messages.append(message)

        print(f'  ✅ {len(messages)}件のメッセージを取得')

        if len(messages) == 0:
            print(f'  ⏭️  メッセージがないためスキップ')
            continue

        # フォーラムスレッドを作成
        print(f'  🔨 フォーラムスレッド作成: {target["thread_title"]}')

        # 最初のメッセージの内容を使用
        first_message_content = messages[0].content if messages[0].content else '（メッセージ内容なし）'

        try:
            thread = await forum_channel.create_thread(
                name=target['thread_title'],
                content=f'**【移行元チャンネル】** {target["channel_name"]}\n\n{first_message_content}'
            )
            print(f'  ✅ スレッド作成完了: {thread.thread.name}')
            await asyncio.sleep(2)
        except Exception as e:
            print(f'  ❌ スレッド作成エラー: {e}')
            continue

        # 残りのメッセージを転記
        if len(messages) > 1:
            print(f'  📝 残り{len(messages) - 1}件のメッセージを転記中...')
            for i, msg in enumerate(messages[1:], start=2):
                try:
                    # 投稿者情報とタイムスタンプを含める
                    content = f'**{msg.author.name}** （{msg.created_at.strftime("%Y-%m-%d %H:%M")}）\n{msg.content}'

                    # 添付ファイルがあれば追加
                    if msg.attachments:
                        content += '\n\n**添付ファイル:**\n' + '\n'.join([att.url for att in msg.attachments])

                    await thread.thread.send(content)
                    print(f'    ✅ メッセージ {i}/{len(messages)} 転記完了')
                    await asyncio.sleep(1)  # レート制限対策
                except Exception as e:
                    print(f'    ❌ メッセージ転記エラー: {e}')

        print(f'  🎉 {target["channel_name"]} の移行完了\n')
        await asyncio.sleep(2)

    print('🎉 全ての移行が完了しました')
    os.system(f'osascript -e \'display notification "既存チャンネルをフォーラムスレッドに移行しました" with title "Discord移行完了"\'')

    await client.close()


if __name__ == '__main__':
    try:
        client.run(TOKEN)
    except Exception as e:
        print(f'❌ エラー: {e}')
