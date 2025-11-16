#!/usr/bin/env python3
"""
Discordに「━━━ プライベート ━━━」カテゴリを作成し、
「📅｜カレンダー登録」チャンネルを作成する

権限: ユーザー、claude_code Bot、Codex Botのみ閲覧可能
"""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# あなたのDiscord User ID（後で設定）
YOUR_USER_ID = None  # 実行時に取得

# Bot User IDs
CLAUDE_CODE_BOT_ID = None  # 実行時に取得
CODEX_BOT_ID = None  # 実行時に取得

# Bot初期化
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Bot起動時にカテゴリとチャンネルを作成"""
    print(f'Bot起動: {bot.user}')

    # サーバー（Guild）を取得
    guild = bot.guilds[0] if bot.guilds else None
    if not guild:
        print('エラー: サーバーが見つかりません')
        await bot.close()
        return

    print(f'サーバー: {guild.name}')

    # メンバーIDを取得
    global YOUR_USER_ID, CLAUDE_CODE_BOT_ID, CODEX_BOT_ID

    # claude_code Botのユーザー（自分自身）
    CLAUDE_CODE_BOT_ID = bot.user.id
    print(f'claude_code Bot ID: {CLAUDE_CODE_BOT_ID}')

    # Codex Botを検索
    for member in guild.members:
        if member.bot and 'codex' in member.name.lower():
            CODEX_BOT_ID = member.id
            print(f'Codex Bot ID: {CODEX_BOT_ID} ({member.name})')
            break

    # あなた（サーバーオーナー or 特定ユーザー）を取得
    # サーバーオーナーを取得
    YOUR_USER_ID = guild.owner_id
    print(f'オーナー User ID: {YOUR_USER_ID}')

    if not CODEX_BOT_ID:
        print('警告: Codex Botが見つかりません。claude_codeとオーナーのみの権限で作成します。')

    # 権限オーバーライドを設定
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),  # @everyone は見えない
        guild.get_member(YOUR_USER_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True),  # オーナー
        bot.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),  # claude_code Bot
    }

    # Codex Botがいれば追加
    if CODEX_BOT_ID:
        codex_member = guild.get_member(CODEX_BOT_ID)
        if codex_member:
            overwrites[codex_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    try:
        # カテゴリ作成
        print('カテゴリ作成中: ━━━ プライベート ━━━')
        category = await guild.create_category(
            name='━━━ プライベート ━━━',
            overwrites=overwrites
        )
        print(f'カテゴリ作成完了: {category.name} (ID: {category.id})')

        # チャンネル作成
        print('チャンネル作成中: 📅｜カレンダー登録')
        channel = await guild.create_text_channel(
            name='📅｜カレンダー登録',
            category=category,
            overwrites=overwrites  # カテゴリと同じ権限
        )
        print(f'チャンネル作成完了: {channel.name} (ID: {channel.id})')

        print('✅ 作成完了')

    except Exception as e:
        print(f'エラー: {e}')

    await bot.close()


if __name__ == "__main__":
    print('━━━ プライベート ━━━ カテゴリ作成スクリプト起動中...')
    bot.run(DISCORD_TOKEN)
