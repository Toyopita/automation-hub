#!/usr/bin/env python3
"""
Discord ⇒ Notion 伝承DB自動登録

Discordの「📖｜伝承投稿」チャンネルの投稿を監視し、
SelectMenuで季節・節気選択、Modalで詳細入力を行います。
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List
import discord
from discord.ui import View, Select, Modal, TextInput
from dotenv import load_dotenv
import requests
from discord_auth_handler import run_with_retry

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TRADITION_CHANNEL_ID = 1438876441226903673  # 📖｜伝承投稿
NOTION_TRADITION_DB_ID = "2ab00160-1818-81ad-b8f5-fe86d2f2b78c"

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[伝承Monitor][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


# 季節・節気の選択肢
SEASONS = [
    "正月", "節分", "春分", "端午", "夏至", "七夕",
    "お盆", "秋分", "冬至", "立春", "立夏", "立秋", "立冬"
]

# 出典の選択肢
SOURCES = ["口伝", "支部員", "親族"]


async def create_notion_tradition(
    name: str,
    season: str,
    overview: str,
    details: str,
    tags: List[str],
    taboo: str,
    source: str
) -> bool:
    """Notionに伝承を作成"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_ORDER")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_ORDERが設定されていません')
            return False

        properties = {
            "名称": {
                "title": [{
                    "type": "text",
                    "text": {"content": name}
                }]
            },
            "概要": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": overview}
                }]
            },
            "詳細・手順": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": details}
                }]
            },
            "季節・節気": {
                "multi_select": [{"name": season}]
            },
            "出典": {
                "multi_select": [{"name": source}]
            }
        }

        # タグを追加
        if tags:
            properties["タグ"] = {
                "multi_select": [{"name": tag} for tag in tags]
            }

        # 禁忌詳細を追加
        if taboo.strip():
            properties["禁忌詳細"] = {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": taboo.strip()}
                }]
            }

        payload = {
            "parent": {"database_id": NOTION_TRADITION_DB_ID},
            "properties": properties
        }

        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
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
                'name': name,
                'season': season
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外', {'error': str(err)})
        return False


class TraditionModal(Modal, title="伝承の詳細を入力"):
    """伝承の詳細入力用Modal"""

    def __init__(self, original_text: str, season: str):
        super().__init__(timeout=600)
        self.original_text = original_text
        self.season = season

        # 元のテキストから名称を推測（最初の一文または20文字）
        first_line = original_text.split('\n')[0]
        suggested_name = first_line[:20] if len(first_line) > 20 else first_line

        self.name_input = TextInput(
            label="名称（伝承の名前）",
            placeholder="例: 節分の豆まき",
            default=suggested_name,
            required=True,
            max_length=100
        )
        self.add_item(self.name_input)

        self.overview_input = TextInput(
            label="概要（1〜2文で要約）",
            placeholder="例: 節分の日に豆を巻いて鬼から家を守る",
            default=original_text[:200] if len(original_text) <= 200 else original_text[:197] + "...",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.overview_input)

        self.details_input = TextInput(
            label="詳細・手順",
            placeholder="例:\n1. 家の各部屋に豆を巻く\n2. 屋根を越すように豆を投げる",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        self.add_item(self.details_input)

        self.tags_input = TextInput(
            label="タグ（カンマ区切り）",
            placeholder="例: 節分, 豆まき, 鬼除け",
            required=False,
            max_length=200
        )
        self.add_item(self.tags_input)

        self.taboo_input = TextInput(
            label="禁忌詳細（あれば）",
            placeholder="例: ○○してはいけない",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.taboo_input)

    async def on_submit(self, interaction: discord.Interaction):
        """詳細入力完了時"""
        name = str(self.name_input.value).strip()
        overview = str(self.overview_input.value).strip()
        details = str(self.details_input.value).strip() if self.details_input.value else ""
        tags_str = str(self.tags_input.value).strip() if self.tags_input.value else ""
        taboo = str(self.taboo_input.value).strip() if self.taboo_input.value else ""

        # タグをリストに変換
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

        await interaction.response.defer(ephemeral=True)

        # 出典選択UIを表示
        view = SourceSelectView(name, self.season, overview, details, tags, taboo)
        await interaction.followup.send(
            f"📝 **出典を選択してください**\n\n"
            f"名称: {name}\n"
            f"季節: {self.season}",
            view=view,
            ephemeral=True
        )


class SourceSelect(Select):
    """出典選択用SelectMenu"""

    def __init__(self, name: str, season: str, overview: str, details: str, tags: List[str], taboo: str):
        options = [
            discord.SelectOption(label=source, value=source)
            for source in SOURCES
        ]

        super().__init__(
            placeholder="出典を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )
        self.name = name
        self.season = season
        self.overview = overview
        self.details = details
        self.tags = tags
        self.taboo = taboo

    async def callback(self, interaction: discord.Interaction):
        """出典選択時"""
        source = self.values[0]

        await interaction.response.defer(ephemeral=True)

        # Notionに登録
        success = await create_notion_tradition(
            self.name,
            self.season,
            self.overview,
            self.details,
            self.tags,
            self.taboo,
            source
        )

        if success:
            tags_display = f"\nタグ: {', '.join(self.tags)}" if self.tags else ""
            taboo_display = f"\n禁忌: {self.taboo}" if self.taboo else ""
            await interaction.followup.send(
                f"✅ 伝承をNotion DBに登録しました\n\n"
                f"**名称:** {self.name}\n"
                f"**季節:** {self.season}\n"
                f"**出典:** {source}{tags_display}{taboo_display}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Notion登録に失敗しました。",
                ephemeral=True
            )


class SourceSelectView(View):
    """出典選択View"""

    def __init__(self, name: str, season: str, overview: str, details: str, tags: List[str], taboo: str, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(SourceSelect(name, season, overview, details, tags, taboo))


class SeasonSelect(Select):
    """季節・節気選択用SelectMenu"""

    def __init__(self, original_text: str):
        options = [
            discord.SelectOption(label=season, value=season)
            for season in SEASONS
        ]

        super().__init__(
            placeholder="季節・節気を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )
        self.original_text = original_text

    async def callback(self, interaction: discord.Interaction):
        """季節・節気選択時"""
        season = self.values[0]

        # 詳細入力Modalを表示
        await interaction.response.send_modal(
            TraditionModal(self.original_text, season)
        )


class SeasonSelectView(View):
    """季節・節気選択View"""

    def __init__(self, original_text: str, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(SeasonSelect(original_text))


@client.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {client.user}')
    log('INFO', f'伝承投稿チャンネル監視開始: {TRADITION_CHANNEL_ID}')


@client.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # 伝承投稿チャンネル以外は無視
    if message.channel.id != TRADITION_CHANNEL_ID:
        return

    message_text = message.content.strip()
    if not message_text:
        await message.add_reaction('❓')
        return

    log('INFO', '伝承投稿受信', {
        'author': str(message.author),
        'content': message_text[:100]
    })

    # 季節・節気選択UIを表示
    view = SeasonSelectView(message_text)

    await message.reply(
        f"📖 **伝承の季節・節気を選択してください**\n\n"
        f"投稿内容: {message_text[:100]}{'...' if len(message_text) > 100 else ''}",
        view=view,
        mention_author=False
    )
    await message.add_reaction('⏳')


if __name__ == "__main__":
    run_with_retry(client, DISCORD_TOKEN, '伝承Monitor')
