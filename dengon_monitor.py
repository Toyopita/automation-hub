#!/usr/bin/env python3
"""
Discord ⇒ Notion 伝言自動登録（UI版）

Discordの「📝｜伝言」チャンネルの投稿を監視し、
Modalで確認後、Notionの伝言管理DBに登録します。

機能:
- 1行目を伝言件名、2行目以降を伝言詳細として解析
- Modalで確認・編集してから登録
- 登録完了後に✅リアクション
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict
import discord
from discord.ui import View, Modal, TextInput, Button
from dotenv import load_dotenv
import requests
from discord_auth_handler import run_with_retry

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DENGON_CHANNEL_ID = 1455308375146627093  # 📝｜伝言
NOTION_DENGON_DB_ID = "8a5b21f3-ac93-4967-b473-a0b68f93c8a8"

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[伝言Monitor][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


def get_notion_token() -> Optional[str]:
    """Notionトークンを取得（伝言DB用）"""
    # NOTION_TOKEN_ORDERを使用（伝言DBに接続済み）
    return os.getenv("NOTION_TOKEN_ORDER")


async def create_notion_dengon(subject: str, detail: str = "", confidential: str = "") -> bool:
    """Notionに伝言を作成"""
    try:
        notion_token = get_notion_token()
        if not notion_token:
            log('ERROR', 'Notionトークンが設定されていません')
            return False

        # 伝言件名と伝言詳細を分離して登録
        properties = {
            "伝言件名": {
                "title": [{
                    "type": "text",
                    "text": {"content": subject}
                }]
            },
            "通知送信": {
                "checkbox": True
            }
        }

        # 伝言詳細がある場合は追加
        if detail.strip():
            properties["伝言詳細"] = {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": detail.strip()}
                }]
            }

        # 機密事項がある場合は追加
        if confidential.strip():
            properties["機密事項"] = {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": confidential.strip()}
                }]
            }

        payload = {
            "parent": {"type": "data_source_id", "data_source_id": NOTION_DENGON_DB_ID},
            "properties": properties
        }

        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2025-09-03',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            'https://api.notion.com/v1/pages',
            headers=headers,
            json=payload
        )

        if response.status_code >= 400:
            error_detail = response.json()
            log('ERROR', 'Notion APIエラー', {
                'code': response.status_code,
                'message': error_detail.get('message')
            })
            return False
        else:
            log('SUCCESS', 'Notion登録成功', {
                'subject': subject,
                'has_detail': bool(detail.strip())
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外', {'error': str(err)})
        return False


class DengonModal(Modal, title="伝言を確認・編集"):
    """伝言確認・編集用Modal"""

    def __init__(self, subject: str, detail: str, original_message: discord.Message):
        super().__init__(timeout=300)
        self.original_message = original_message

        self.subject_input = TextInput(
            label="伝言件名",
            placeholder="伝言の件名を入力",
            default=subject,
            required=True,
            max_length=200
        )
        self.add_item(self.subject_input)

        self.detail_input = TextInput(
            label="伝言詳細（任意）",
            placeholder="詳細を入力（任意）",
            default=detail,
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        self.add_item(self.detail_input)

        self.confidential_input = TextInput(
            label="機密事項（任意）",
            placeholder="機密情報を入力（任意・LINEには送信されません）",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        self.add_item(self.confidential_input)

    async def on_submit(self, interaction: discord.Interaction):
        """送信ボタン押下時"""
        subject = str(self.subject_input.value).strip()
        detail = str(self.detail_input.value).strip() if self.detail_input.value else ""
        confidential = str(self.confidential_input.value).strip() if self.confidential_input.value else ""

        if not subject:
            await interaction.response.send_message(
                "❌ 伝言件名は必須です。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Notionに登録
        success = await create_notion_dengon(subject, detail, confidential)

        # 元のメッセージのリアクションを更新
        try:
            await self.original_message.remove_reaction('⏳', client.user)
        except:
            pass

        if success:
            await self.original_message.add_reaction('✅')
            detail_info = f"\n📄 伝言詳細: {detail[:100]}{'...' if len(detail) > 100 else ''}" if detail else ""
            confidential_info = f"\n🔒 機密事項: あり" if confidential else ""
            await interaction.followup.send(
                f"✅ 伝言を登録しました\n"
                f"📝 伝言件名: {subject}{detail_info}{confidential_info}",
                ephemeral=True
            )
        else:
            await self.original_message.add_reaction('❌')
            await interaction.followup.send(
                "❌ 伝言の登録に失敗しました。",
                ephemeral=True
            )


class DengonConfirmView(View):
    """伝言確認用View - 1ボタンで即Modal表示"""

    def __init__(self, subject: str, detail: str, original_message: discord.Message, timeout=180):
        super().__init__(timeout=timeout)
        self.subject = subject
        self.detail = detail
        self.original_message = original_message

    @discord.ui.button(label="ここをクリックして登録", style=discord.ButtonStyle.primary, emoji="📝")
    async def open_modal_button(self, interaction: discord.Interaction, button: Button):
        """即座にModalを表示"""
        await interaction.response.send_modal(
            DengonModal(self.subject, self.detail, self.original_message)
        )

    async def on_timeout(self):
        """タイムアウト時"""
        try:
            await self.original_message.remove_reaction('⏳', client.user)
            await self.original_message.add_reaction('⏰')
        except:
            pass


@client.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {client.user}')
    log('INFO', f'伝言チャンネル監視開始: {DENGON_CHANNEL_ID}')


def parse_dengon_message(text: str) -> Dict[str, str]:
    """
    伝言メッセージをパース

    対応形式:
    1. 明示形式:
       伝言件名: 電話あり
       伝言詳細: ○○様から折り返し希望

    2. 簡略形式（1行のみ）:
       電話あり
       → 伝言件名のみ

    3. 簡略形式（複数行）:
       電話あり
       ○○様から折り返し希望
       → 1行目が伝言件名、2行目以降が伝言詳細
    """
    result = {"伝言件名": "", "伝言詳細": ""}

    lines = text.strip().split('\n')

    # 明示形式かチェック
    has_explicit_format = False
    for line in lines:
        if line.startswith('伝言件名:') or line.startswith('伝言件名：'):
            has_explicit_format = True
            break

    if has_explicit_format:
        # 明示形式でパース
        current_key = None
        current_value = []

        for line in lines:
            if line.startswith('伝言件名:') or line.startswith('伝言件名：'):
                if current_key and current_value:
                    result[current_key] = '\n'.join(current_value).strip()
                current_key = "伝言件名"
                value = line.split(':', 1)[1] if ':' in line else line.split('：', 1)[1]
                current_value = [value.strip()]
            elif line.startswith('伝言詳細:') or line.startswith('伝言詳細：'):
                if current_key and current_value:
                    result[current_key] = '\n'.join(current_value).strip()
                current_key = "伝言詳細"
                value = line.split(':', 1)[1] if ':' in line else line.split('：', 1)[1]
                current_value = [value.strip()]
            elif current_key:
                current_value.append(line)

        if current_key and current_value:
            result[current_key] = '\n'.join(current_value).strip()
    else:
        # 簡略形式でパース
        if len(lines) == 1:
            result["伝言件名"] = lines[0].strip()
        else:
            result["伝言件名"] = lines[0].strip()
            result["伝言詳細"] = '\n'.join(lines[1:]).strip()

    return result


@client.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # 伝言チャンネル以外は無視
    if message.channel.id != DENGON_CHANNEL_ID:
        return

    message_text = message.content.strip()
    if not message_text:
        await message.add_reaction('❓')
        return

    log('INFO', '伝言受信', {
        'author': str(message.author),
        'content': message_text[:100]
    })

    # メッセージをパース
    parsed = parse_dengon_message(message_text)
    subject = parsed["伝言件名"]
    detail = parsed["伝言詳細"]

    if not subject:
        await message.add_reaction('❓')
        await message.reply(
            "❓ 伝言件名が見つかりません。\n\n"
            "**投稿形式:**\n"
            "```\n"
            "伝言件名: 電話あり\n"
            "伝言詳細: ○○様から折り返し希望\n"
            "```\n"
            "または簡略形式（1行目が件名）:\n"
            "```\n"
            "電話あり\n"
            "```",
            mention_author=False
        )
        return

    # 処理中リアクション
    await message.add_reaction('⏳')

    # 即座にボタン表示（クリックでModal）
    view = DengonConfirmView(subject, detail, message)

    await message.reply(
        "📝 **ボタンをクリックして伝言を登録**",
        view=view,
        mention_author=False
    )


if __name__ == "__main__":
    run_with_retry(client, DISCORD_TOKEN, '伝言Monitor')
