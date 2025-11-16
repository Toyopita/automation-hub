#!/usr/bin/env python3
"""
Discord チャンネル自動アーカイブスクリプト

3ヶ月以上更新がないチャンネルを自動的にアーカイブカテゴリに移動します。
- 対象: 「祭礼進行中」「行事進行中」カテゴリ内のチャンネル/フォーラム
- 移動先: 「祭礼アーカイブ」「行事アーカイブ」カテゴリ
"""

import os
import discord
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import asyncio
import logging

# ログ設定
LOG_FILE = os.path.expanduser("~/discord-mcp-server/auto_archive.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 環境変数読み込み
load_dotenv(os.path.expanduser("~/discord-mcp-server/.env"))
TOKEN = os.getenv("DISCORD_TOKEN")

# 設定
DRY_RUN = False  # True: 移動せず対象を表示のみ / False: 実際に移動
ARCHIVE_DAYS = 90  # 90日（3ヶ月）

# カテゴリマッピング
CATEGORY_MAPPING = {
    "━━━ 祭礼｜進行中 ━━━": "━━━ 祭礼｜アーカイブ ━━━",
    "━━━ 行事｜進行中 ━━━": "━━━ 行事｜アーカイブ ━━━"
}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def get_last_message_date(channel):
    """チャンネルの最終メッセージ日時を取得"""
    try:
        # フォーラムチャンネルの場合
        if isinstance(channel, discord.ForumChannel):
            last_date = None
            for thread in channel.threads:
                async for message in thread.history(limit=1):
                    if not last_date or message.created_at > last_date:
                        last_date = message.created_at
            return last_date

        # テキストチャンネルの場合
        elif isinstance(channel, discord.TextChannel):
            async for message in channel.history(limit=1):
                return message.created_at
            return None

        else:
            return None
    except discord.errors.Forbidden:
        logging.warning(f"権限不足: {channel.name} の履歴を取得できません")
        return None
    except Exception as e:
        logging.error(f"エラー: {channel.name} の履歴取得中 - {e}")
        return None


async def archive_old_channels():
    """3ヶ月以上更新がないチャンネルをアーカイブに移動"""

    # 出雲組サーバーを取得
    izumo_guild = None
    logging.info(f"接続中のサーバー一覧:")
    for guild in client.guilds:
        logging.info(f"  - {guild.name}")
        if 'IZUMO' in guild.name or '出雲' in guild.name:
            izumo_guild = guild
            break

    if not izumo_guild:
        logging.error('IZUMOサーバーが見つかりません')
        return

    logging.info(f"サーバー: {izumo_guild.name}")
    logging.info(f"モード: {'ドライラン（移動なし）' if DRY_RUN else '実行モード'}")
    logging.info(f"基準日: {ARCHIVE_DAYS}日以上更新なし")
    logging.info("-" * 60)

    # カテゴリを取得
    categories = {}
    for channel in izumo_guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            categories[channel.name] = channel

    now = datetime.now(timezone.utc)
    threshold_date = now - timedelta(days=ARCHIVE_DAYS)

    moved_count = 0

    # 進行中カテゴリをチェック
    for source_category_name, archive_category_name in CATEGORY_MAPPING.items():

        source_category = categories.get(source_category_name)
        archive_category = categories.get(archive_category_name)

        if not source_category:
            logging.warning(f"カテゴリが見つかりません: {source_category_name}")
            continue

        if not archive_category:
            logging.warning(f"アーカイブカテゴリが見つかりません: {archive_category_name}")
            continue

        logging.info(f"\n📁 カテゴリチェック: {source_category_name}")

        # カテゴリ内のチャンネルをチェック
        for channel in source_category.channels:
            if not isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
                continue

            last_message_date = await get_last_message_date(channel)

            if last_message_date is None:
                logging.info(f"  ⏭️  {channel.name}: メッセージなし（スキップ）")
                continue

            days_since_update = (now - last_message_date).days

            if last_message_date < threshold_date:
                logging.info(f"  📦 {channel.name}: {days_since_update}日前 → アーカイブ対象")

                if not DRY_RUN:
                    try:
                        await channel.edit(category=archive_category)
                        logging.info(f"     ✅ 移動完了: {archive_category_name}")
                        moved_count += 1
                    except discord.errors.Forbidden:
                        logging.error(f"     ❌ 権限不足: 移動できません")
                    except Exception as e:
                        logging.error(f"     ❌ エラー: {e}")
                else:
                    moved_count += 1
            else:
                logging.info(f"  ✅ {channel.name}: {days_since_update}日前（継続中）")

    logging.info("-" * 60)
    logging.info(f"完了: {moved_count}件のチャンネルが対象")

    # macOS通知
    if moved_count > 0:
        mode_text = "（ドライラン）" if DRY_RUN else ""
        os.system(f'osascript -e \'display notification "{moved_count}件のチャンネルをアーカイブ対象として検出{mode_text}" with title "Discord自動アーカイブ"\'')


@client.event
async def on_ready():
    logging.info(f'Bot接続成功: {client.user.name}')
    await archive_old_channels()
    await client.close()


if __name__ == "__main__":
    try:
        client.run(TOKEN)
    except Exception as e:
        logging.error(f"実行エラー: {e}")
