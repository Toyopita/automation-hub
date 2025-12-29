#!/usr/bin/env python3
"""
伝言管理DB監視スクリプト
NotionのDBに新しい伝言が追加されたらLINEグループに通知する
"""

import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 設定
NOTION_TOKEN = os.getenv("NOTION_TOKEN_ORDER")  # MCPと同じトークン
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_USER_ID")  # 実際はグループID（Cから始まる）
NOTION_DB_ID = "8a5b21f3-ac93-4967-b473-a0b68f93c8a8"
POLLING_INTERVAL = 10  # 秒

# APIエンドポイント
NOTION_API_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2025-09-03"  # data_sources エンドポイント使用
LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def log(message: str):
    """タイムスタンプ付きログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_unnotified_messages() -> list:
    """通知済み=falseの伝言を取得"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION
    }

    payload = {
        "filter": {
            "property": "通知済み",
            "checkbox": {
                "equals": False
            }
        },
        "sorts": [
            {
                "property": "作成日時",
                "direction": "ascending"
            }
        ]
    }

    try:
        response = requests.post(
            f"{NOTION_API_URL}/data_sources/{NOTION_DB_ID}/query",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            log(f"Notion API エラー: {response.status_code} - {response.text}")
            return []

        data = response.json()
        return data.get("results", [])

    except Exception as e:
        log(f"Notion取得エラー: {e}")
        return []


def extract_message_content(page: dict) -> tuple[str, str]:
    """ページから伝言件名と伝言詳細を抽出"""
    try:
        properties = page.get("properties", {})

        # 伝言件名（タイトル）
        title_prop = properties.get("伝言件名", {})
        title_array = title_prop.get("title", [])
        subject = title_array[0].get("text", {}).get("content", "") if title_array else ""

        # 伝言詳細（テキスト）
        detail_prop = properties.get("伝言詳細", {})
        detail_array = detail_prop.get("rich_text", [])
        detail = detail_array[0].get("text", {}).get("content", "") if detail_array else ""

        return subject, detail

    except Exception as e:
        log(f"内容抽出エラー: {e}")
        return "（件名なし）", ""


def send_line_notification(subject: str, detail: str) -> bool:
    """LINEグループに通知を送信"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    # メッセージを組み立て
    message_lines = ["📝 伝言通知", "", f"【{subject}】"]
    if detail:
        message_lines.append("")
        message_lines.append(detail)

    message_text = "\n".join(message_lines)

    payload = {
        "to": LINE_GROUP_ID,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }

    try:
        response = requests.post(LINE_API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            log(f"LINE通知成功: {subject}")
            return True
        else:
            log(f"LINE API エラー: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"LINE送信エラー: {e}")
        return False


def mark_as_notified(page_id: str) -> bool:
    """通知済みフラグをtrueに更新"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "properties": {
            "通知済み": {
                "checkbox": True
            }
        }
    }

    try:
        response = requests.patch(
            f"{NOTION_API_URL}/pages/{page_id}",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            log(f"通知済みフラグ更新成功: {page_id}")
            return True
        else:
            log(f"Notion更新エラー: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        log(f"Notion更新エラー: {e}")
        return False


def process_new_messages():
    """新規伝言を処理"""
    messages = get_unnotified_messages()

    if not messages:
        return

    log(f"未通知の伝言: {len(messages)}件")

    for page in messages:
        page_id = page.get("id")
        subject, detail = extract_message_content(page)

        log(f"処理中: {subject}")

        # LINE通知を送信
        if send_line_notification(subject, detail):
            # 成功したら通知済みフラグを更新
            mark_as_notified(page_id)
        else:
            log(f"通知失敗、次回リトライ: {page_id}")


def validate_config():
    """設定の検証"""
    errors = []

    if not NOTION_TOKEN:
        errors.append("NOTION_TOKEN_ORDER が設定されていません")
    if not LINE_CHANNEL_ACCESS_TOKEN:
        errors.append("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
    if not LINE_GROUP_ID:
        errors.append("LINE_USER_ID (グループID) が設定されていません")

    if errors:
        for error in errors:
            log(f"設定エラー: {error}")
        return False

    return True


def main():
    """メインループ"""
    log("=" * 50)
    log("伝言管理DB監視スクリプト起動")
    log(f"ポーリング間隔: {POLLING_INTERVAL}秒")
    log(f"Notion DB ID: {NOTION_DB_ID}")
    log("=" * 50)

    if not validate_config():
        log("設定エラーのため終了します")
        return

    log("監視を開始します...")

    try:
        while True:
            process_new_messages()
            time.sleep(POLLING_INTERVAL)

    except KeyboardInterrupt:
        log("監視を終了します")


if __name__ == "__main__":
    main()
