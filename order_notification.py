#!/usr/bin/env python3
"""
Notion ⇒ MacBook ⇒ Discord ―― 発注履歴通知Bot

Notion「祖霊社_記念品発注管理」DBに新規ページが追加されたり、
更新されたりした場合、Discordの「📋｜発注ログ」チャンネルに通知します。

発注履歴DB ID: 1ca00160-1818-8023-b120-ee4dd54fc2c3
発注ログチャンネルID: 1430362512225996840
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN_TASK")  # 発注履歴DB用のトークン（既存のトークンを使用）
ORDER_LOG_CHANNEL_ID = 1430362512225996840
NOTION_DB_ID = "1ca00160-1818-8023-b120-ee4dd54fc2c3"

# チェック間隔（秒）
CHECK_INTERVAL = 300  # 5分ごと

# 最後にチェックした時刻を保存するファイル
LAST_CHECK_FILE = "/Users/minamitakeshi/discord-mcp-server/.last_order_check"

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[発注通知][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg, flush=True)


def get_last_check_time() -> datetime:
    """最後にチェックした時刻を取得"""
    try:
        if os.path.exists(LAST_CHECK_FILE):
            with open(LAST_CHECK_FILE, 'r') as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str)
        else:
            # 初回起動時は24時間前から
            return datetime.now(timezone.utc) - timedelta(hours=24)
    except Exception as e:
        log('ERROR', 'last_check_time読み込みエラー', {'error': str(e)})
        return datetime.now(timezone.utc) - timedelta(hours=24)


def save_last_check_time(check_time: datetime):
    """最後にチェックした時刻を保存"""
    try:
        with open(LAST_CHECK_FILE, 'w') as f:
            f.write(check_time.isoformat())
        log('DEBUG', '最終チェック時刻保存', {'time': check_time.isoformat()})
    except Exception as e:
        log('ERROR', 'last_check_time保存エラー', {'error': str(e)})


def query_notion_db(last_check: datetime) -> List[Dict]:
    """
    Notion DBをクエリして、last_check以降に作成/更新されたページを取得

    Args:
        last_check: 前回チェック時刻

    Returns:
        新規/更新されたページのリスト
    """
    try:
        headers = {
            'Authorization': f'Bearer {NOTION_TOKEN}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }

        # Notion APIはISO 8601形式を要求
        last_check_iso = last_check.isoformat()

        payload = {
            "filter": {
                "or": [
                    {
                        "timestamp": "created_time",
                        "created_time": {
                            "after": last_check_iso
                        }
                    },
                    {
                        "timestamp": "last_edited_time",
                        "last_edited_time": {
                            "after": last_check_iso
                        }
                    }
                ]
            },
            "sorts": [
                {
                    "timestamp": "created_time",
                    "direction": "descending"
                }
            ]
        }

        response = requests.post(
            f'https://api.notion.com/v1/databases/{NOTION_DB_ID}/query',
            headers=headers,
            json=payload
        )

        log('DEBUG', 'Notion APIレスポンス', {'code': response.status_code})

        if response.status_code >= 400:
            error_detail = response.json()
            log('ERROR', 'Notion APIエラー', {
                'code': response.status_code,
                'message': error_detail.get('message')
            })
            return []

        data = response.json()
        results = data.get('results', [])
        log('INFO', f'{len(results)}件の新規/更新ページを検出')
        return results

    except Exception as err:
        log('ERROR', 'Notion DB クエリ例外', {'error': str(err)})
        return []


def extract_page_data(page: Dict) -> Dict:
    """
    Notionページからデータを抽出

    Args:
        page: Notionページオブジェクト

    Returns:
        抽出したデータ
    """
    try:
        properties = page.get('properties', {})

        # 商品名
        title_prop = properties.get('商品名', {})
        title_list = title_prop.get('title', [])
        product_name = title_list[0].get('plain_text', '') if title_list else '（商品名なし）'

        # 数量
        quantity_prop = properties.get('数量', {})
        quantity = quantity_prop.get('number', 0) or 0

        # 単価
        unit_price_prop = properties.get('単価', {})
        unit_price = unit_price_prop.get('number', 0) or 0

        # 合計金額（formula）
        total_prop = properties.get('合計金額', {})
        total_formula = total_prop.get('formula', {})
        total = total_formula.get('number', 0) or 0

        # 納品予定日
        delivery_date_prop = properties.get('納品予定日', {})
        delivery_date_obj = delivery_date_prop.get('date', {})
        delivery_date = delivery_date_obj.get('start', '') if delivery_date_obj else ''

        # 進捗
        status_prop = properties.get('進捗', {})
        status_obj = status_prop.get('status', {})
        status = status_obj.get('name', '未了') if status_obj else '未了'

        # 作成時刻
        created_time = page.get('created_time', '')

        # ページURL
        page_url = page.get('url', '')

        return {
            'product_name': product_name,
            'quantity': quantity,
            'unit_price': unit_price,
            'total': total,
            'delivery_date': delivery_date,
            'status': status,
            'created_time': created_time,
            'page_url': page_url
        }

    except Exception as e:
        log('ERROR', 'ページデータ抽出エラー', {'error': str(e)})
        return {}


async def send_discord_notification(data: Dict):
    """
    Discordに発注履歴通知を送信

    Args:
        data: 抽出したデータ
    """
    try:
        channel = bot.get_channel(ORDER_LOG_CHANNEL_ID)
        if not channel:
            log('ERROR', 'チャンネルが見つかりません', {'channel_id': ORDER_LOG_CHANNEL_ID})
            return

        # メッセージフォーマット
        message = f"""# 📦 新規発注登録

**商品名**: {data['product_name']}
**数量**: {data['quantity']}個
**単価**: ¥{data['unit_price']:,}
**合計金額**: ¥{data['total']:,}
**納品予定日**: {data['delivery_date'] or '未定'}
**進捗**: {data['status']}

[Notionで確認]({data['page_url']})"""

        await channel.send(message)
        log('SUCCESS', 'Discord通知送信完了', {'product': data['product_name']})

    except Exception as e:
        log('ERROR', 'Discord通知送信エラー', {'error': str(e)})


async def check_notion_updates():
    """Notion DBをチェックして更新を検出"""
    while True:
        try:
            log('INFO', '発注履歴DBチェック開始')

            # 前回チェック時刻を取得
            last_check = get_last_check_time()
            log('DEBUG', '前回チェック時刻', {'time': last_check.isoformat()})

            # Notion DBをクエリ
            pages = query_notion_db(last_check)

            # 各ページについて通知を送信
            for page in pages:
                data = extract_page_data(page)
                if data:
                    await send_discord_notification(data)
                    await asyncio.sleep(2)  # 連続投稿を避けるため

            # 最終チェック時刻を更新
            current_time = datetime.now(timezone.utc)
            save_last_check_time(current_time)

            log('INFO', f'次回チェックまで{CHECK_INTERVAL}秒待機')
            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            log('ERROR', 'チェック処理例外', {'error': str(e)})
            await asyncio.sleep(60)  # エラー時は1分待機


@bot.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {bot.user}')
    log('INFO', f'発注ログチャンネル監視開始: {ORDER_LOG_CHANNEL_ID}')

    # バックグラウンドタスクとして定期チェックを開始
    bot.loop.create_task(check_notion_updates())


if __name__ == "__main__":
    log('INFO', '発注履歴通知Bot起動中...')
    bot.run(DISCORD_TOKEN)
