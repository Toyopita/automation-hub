#!/usr/bin/env python3
"""
Discord ⇒ Notion 献品管理システム

Discordの献品チャンネルの投稿を監視し、
「米」または「酒」の投稿に反応して種類選択UIを表示します。

機能:
- 献米: 種類選択 → キロ数・袋数入力 → Notion自動登録
- 献酒: 種類選択 → 本数入力 → Notion自動登録
- 奉納年月は自動設定
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict
import discord
from discord.ui import View, Select, Modal, TextInput
from dotenv import load_dotenv
import requests
from discord_auth_handler import run_with_retry

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
KENPIN_CHANNEL_IDS = [
    1435510401600327781   # 献品（IZUMOサーバー）
]

# NotionデータベースID
RICE_DB = "28000160-1818-80a1-94e3-f87262777dec"  # 献米DB
SAKE_DB = "18700160-1818-802b-afef-d94a672cee11"  # 献酒DB

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[献品Bot][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


async def create_rice_entry(rice_type: str, kg_per_bag: int, bag_count: int, bunrui: str, month: str) -> bool:
    """献米DBにエントリ作成"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_RICE")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_RICEが設定されていません')
            return False

        # 現在の年を取得
        current_year = str(datetime.now().year)

        properties = {
            "商品名": {
                "title": [{"type": "text", "text": {"content": rice_type}}]
            },
            "キロ数": {
                "number": kg_per_bag
            },
            "数量": {
                "number": bag_count
            },
            "分類": {
                "select": {"name": bunrui}
            },
            "奉納年": {
                "select": {"name": current_year}
            },
            "奉納月": {
                "select": {"name": month}
            }
        }

        payload = {
            "parent": {"database_id": RICE_DB},
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
            log('ERROR', 'Notion APIエラー（献米）', {
                'code': response.status_code,
                'message': error_detail.get('message')
            })
            return False
        else:
            log('SUCCESS', 'Notion登録成功（献米）', {
                'type': rice_type,
                'kg_per_bag': kg_per_bag,
                'bag_count': bag_count,
                'total_kg': kg_per_bag * bag_count,
                'bunrui': bunrui,
                'month': month
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外（献米）', {'error': str(err)})
        return False


async def create_sake_entry(sake_type: str, bottle_count: int, bunrui: str, month: str) -> bool:
    """献酒DBにエントリ作成"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_SAKE")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_SAKEが設定されていません')
            return False

        # 現在の年を取得
        current_year = str(datetime.now().year)

        properties = {
            "商品名": {
                "title": [{"type": "text", "text": {"content": sake_type}}]
            },
            "数量": {
                "number": bottle_count
            },
            "分類": {
                "select": {"name": bunrui}
            },
            "奉納年": {
                "select": {"name": current_year}
            },
            "奉納月": {
                "select": {"name": month}
            }
        }

        payload = {
            "parent": {"database_id": SAKE_DB},
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
            log('ERROR', 'Notion APIエラー（献酒）', {
                'code': response.status_code,
                'message': error_detail.get('message')
            })
            return False
        else:
            log('SUCCESS', 'Notion登録成功（献酒）', {
                'type': sake_type,
                'bottle_count': bottle_count,
                'bunrui': bunrui,
                'month': month
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外（献酒）', {'error': str(err)})
        return False


class RiceModal(Modal, title="献米情報入力"):
    """献米情報入力用Modal"""

    def __init__(self, rice_type: str, bunrui: str, month: str):
        super().__init__(timeout=300)
        self.rice_type = rice_type
        self.bunrui = bunrui
        self.month = month

        self.kg_input = TextInput(
            label="1袋あたりのキロ数",
            placeholder="例: 30",
            required=True,
            max_length=10
        )
        self.add_item(self.kg_input)

        self.bag_count_input = TextInput(
            label="袋数",
            placeholder="例: 5",
            required=True,
            max_length=10
        )
        self.add_item(self.bag_count_input)

    async def on_submit(self, interaction: discord.Interaction):
        """入力完了時"""
        try:
            kg_per_bag = int(self.kg_input.value.strip())
            bag_count = int(self.bag_count_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "⚠️ キロ数と袋数は数字で入力してください。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success = await create_rice_entry(self.rice_type, kg_per_bag, bag_count, self.bunrui, self.month)

        if success:
            total_kg = kg_per_bag * bag_count
            result_msg = (
                f"✅ 献米登録完了\n\n"
                f"🌾 種類: {self.rice_type}\n"
                f"⚖️ 1袋あたり: {kg_per_bag}kg\n"
                f"📦 袋数: {bag_count}袋\n"
                f"📊 合計: {total_kg}kg\n"
                f"📂 分類: {self.bunrui}\n"
                f"📅 奉納月: {self.month}月"
            )

            # 続けて登録ボタンを表示
            view = ContinueRiceRegistrationView(self.bunrui, self.month)
            await interaction.followup.send(result_msg, view=view, ephemeral=True)
        else:
            await interaction.followup.send(
                "⚠️ Notion登録に失敗しました。",
                ephemeral=True
            )


class SakeModal(Modal, title="献酒情報入力"):
    """献酒情報入力用Modal"""

    def __init__(self, sake_type: str, bunrui: str, month: str):
        super().__init__(timeout=300)
        self.sake_type = sake_type
        self.bunrui = bunrui
        self.month = month

        self.bottle_count_input = TextInput(
            label="本数",
            placeholder="例: 10",
            required=True,
            max_length=10
        )
        self.add_item(self.bottle_count_input)

    async def on_submit(self, interaction: discord.Interaction):
        """入力完了時"""
        try:
            bottle_count = int(self.bottle_count_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "⚠️ 本数は数字で入力してください。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success = await create_sake_entry(self.sake_type, bottle_count, self.bunrui, self.month)

        if success:
            result_msg = (
                f"✅ 献酒登録完了\n\n"
                f"🍶 種類: {self.sake_type}\n"
                f"🍾 本数: {bottle_count}本\n"
                f"📂 分類: {self.bunrui}\n"
                f"📅 奉納月: {self.month}月"
            )
            await interaction.followup.send(result_msg, ephemeral=True)
        else:
            await interaction.followup.send(
                "⚠️ Notion登録に失敗しました。",
                ephemeral=True
            )


class SakeBulkModal(Modal, title="献酒一括登録"):
    """献酒一括登録用Modal"""

    def __init__(self, sake_types: list, bunrui: str, month: str):
        super().__init__(timeout=300)
        self.sake_types = sake_types
        self.bunrui = bunrui
        self.month = month
        self.inputs = {}

        # 選択された種類分の入力フィールドを生成（最大5個）
        for sake_type in sake_types[:5]:
            text_input = TextInput(
                label=f"{sake_type}の本数",
                placeholder="例: 10（0や空欄はスキップ）",
                required=False,
                max_length=10
            )
            self.inputs[sake_type] = text_input
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        """入力完了時"""
        await interaction.response.defer(ephemeral=True)

        success_count = 0
        error_count = 0
        results = []

        for sake_type, text_input in self.inputs.items():
            value = text_input.value.strip() if text_input.value else ""

            # 空欄または0はスキップ
            if not value or value == "0":
                continue

            try:
                bottle_count = int(value)
                success = await create_sake_entry(sake_type, bottle_count, self.bunrui, self.month)

                if success:
                    success_count += 1
                    results.append(f"✅ {sake_type}: {bottle_count}本")
                else:
                    error_count += 1
                    results.append(f"❌ {sake_type}: 登録失敗")
            except ValueError:
                error_count += 1
                results.append(f"⚠️ {sake_type}: 数字が無効")

        result_msg = (
            f"📊 献酒一括登録完了\n\n"
            f"📂 分類: {self.bunrui}\n"
            f"📅 奉納月: {self.month}月\n\n"
            f"✅ 成功: {success_count}件\n"
            f"❌ エラー: {error_count}件\n\n"
            + "\n".join(results)
        )

        await interaction.followup.send(result_msg, ephemeral=True)


class ContinueRiceRegistrationButton(discord.ui.Button):
    """続けて登録ボタン"""

    def __init__(self, bunrui: str, month: str):
        super().__init__(label="続けて登録する", style=discord.ButtonStyle.primary)
        self.bunrui = bunrui
        self.month = month

    async def callback(self, interaction: discord.Interaction):
        """ボタン押下時"""
        # 種類選択へ戻る
        view = RiceTypeSelectView(self.bunrui, self.month)
        await interaction.response.edit_message(
            content=f"🌾 献米の種類を選択してください：\n\n📂 分類: {self.bunrui}\n📅 奉納月: {self.month}月",
            view=view
        )


class ContinueRiceRegistrationView(View):
    """続けて登録View"""

    def __init__(self, bunrui: str, month: str, timeout=180):
        super().__init__(timeout=timeout)
        self.bunrui = bunrui
        self.month = month
        self.add_item(ContinueRiceRegistrationButton(bunrui, month))


class RiceTypeSelect(Select):
    """献米種類選択用SelectMenu"""

    def __init__(self, bunrui: str, month: str):
        self.bunrui = bunrui
        self.month = month

        options = [
            discord.SelectOption(label="白", value="白"),
            discord.SelectOption(label="黒", value="黒"),
            discord.SelectOption(label="モチ", value="モチ"),
            discord.SelectOption(label="その他", value="その他"),
        ]

        super().__init__(
            placeholder="献米の種類を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """種類選択時"""
        rice_type = self.values[0]

        # Modalを表示
        await interaction.response.send_modal(RiceModal(rice_type, self.bunrui, self.month))


class RiceTypeSelectView(View):
    """献米種類選択View"""

    def __init__(self, bunrui: str, month: str, timeout=180):
        super().__init__(timeout=timeout)
        self.bunrui = bunrui
        self.month = month
        self.add_item(RiceTypeSelect(bunrui, month))




class BunruiSelect(Select):
    """分類選択用SelectMenu"""

    def __init__(self, kenpin_category: str, item_type: str = None):
        self.kenpin_category = kenpin_category
        self.item_type = item_type  # 献米の場合のみ使用

        options = [
            discord.SelectOption(label="本部", value="本部"),
            discord.SelectOption(label="祖霊社", value="祖霊社"),
            discord.SelectOption(label="使用", value="使用"),
            discord.SelectOption(label="未設定", value="未設定"),
        ]

        super().__init__(
            placeholder="分類を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """分類選択時"""
        bunrui = self.values[0]

        # 奉納月選択へ進む
        view = MonthSelectView(self.kenpin_category, bunrui, self.item_type)
        await interaction.response.edit_message(
            content=f"📅 奉納月を選択してください：",
            view=view
        )


class BunruiSelectView(View):
    """分類選択View"""

    def __init__(self, kenpin_category: str, item_type: str = None, timeout=180):
        super().__init__(timeout=timeout)
        self.kenpin_category = kenpin_category
        self.item_type = item_type  # 献米の場合のみ使用
        self.add_item(BunruiSelect(kenpin_category, item_type))


class MonthSelect(Select):
    """奉納月選択用SelectMenu"""

    def __init__(self, kenpin_category: str, bunrui: str, item_type: str = None):
        self.kenpin_category = kenpin_category
        self.item_type = item_type  # 献米の場合のみ使用
        self.bunrui = bunrui

        options = [
            discord.SelectOption(label="1月", value="1"),
            discord.SelectOption(label="2月", value="2"),
            discord.SelectOption(label="3月", value="3"),
            discord.SelectOption(label="4月", value="4"),
            discord.SelectOption(label="5月", value="5"),
            discord.SelectOption(label="6月", value="6"),
            discord.SelectOption(label="7月", value="7"),
            discord.SelectOption(label="8月", value="8"),
            discord.SelectOption(label="9月", value="9"),
            discord.SelectOption(label="10月", value="10"),
            discord.SelectOption(label="11月", value="11"),
            discord.SelectOption(label="12月", value="12"),
        ]

        super().__init__(
            placeholder="奉納月を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """奉納月選択時"""
        month = self.values[0]

        if self.kenpin_category == 'rice':
            # 献米は種類選択へ進む
            view = RiceTypeSelectView(self.bunrui, month)
            await interaction.response.edit_message(
                content=f"🌾 献米の種類を選択してください：",
                view=view
            )
        else:  # sake
            # 献酒は種類の複数選択へ進む
            view = SakeTypeMultiSelectView(self.bunrui, month)
            await interaction.response.edit_message(
                content=f"🍶 献酒の種類を選択してください（複数選択可、最大5種類）：",
                view=view
            )


class MonthSelectView(View):
    """奉納月選択View"""

    def __init__(self, kenpin_category: str, bunrui: str, item_type: str = None, timeout=180):
        super().__init__(timeout=timeout)
        self.kenpin_category = kenpin_category
        self.item_type = item_type  # 献米の場合のみ使用
        self.bunrui = bunrui
        self.add_item(MonthSelect(kenpin_category, bunrui, item_type))


class SakeTypeMultiSelect(Select):
    """献酒種類複数選択用SelectMenu"""

    def __init__(self, bunrui: str, month: str):
        self.bunrui = bunrui
        self.month = month

        options = [
            discord.SelectOption(label="賀茂鶴", value="賀茂鶴"),
            discord.SelectOption(label="樽酒", value="樽酒"),
            discord.SelectOption(label="上撰", value="上撰"),
            discord.SelectOption(label="飛翔", value="飛翔"),
            discord.SelectOption(label="典雅", value="典雅"),
            discord.SelectOption(label="その他", value="その他"),
        ]

        super().__init__(
            placeholder="献酒の種類を選択（複数選択可、最大5種類）",
            min_values=1,
            max_values=5,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """種類複数選択時"""
        sake_types = self.values

        # 一括登録Modalを表示
        await interaction.response.send_modal(SakeBulkModal(sake_types, self.bunrui, self.month))


class SakeTypeMultiSelectView(View):
    """献酒種類複数選択View"""

    def __init__(self, bunrui: str, month: str, timeout=180):
        super().__init__(timeout=timeout)
        self.bunrui = bunrui
        self.month = month
        self.add_item(SakeTypeMultiSelect(bunrui, month))




@client.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {client.user}')
    log('INFO', f'献品チャンネル監視開始: {KENPIN_CHANNEL_IDS}')


@client.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # 献品チャンネル以外は無視
    if message.channel.id not in KENPIN_CHANNEL_IDS:
        return

    content = message.content.strip()
    if not content:
        await message.add_reaction('❓')
        return

    # 「米」または「酒」を判定
    if content in ['米', 'こめ', 'コメ', 'rice']:
        kenpin_category = 'rice'
        category_label = '🌾 献米'

        log('INFO', '献品受信', {
            'author': str(message.author),
            'category': kenpin_category
        })

        # 献米: 分類選択から開始
        view = BunruiSelectView(kenpin_category, None)
        await message.reply(
            f"{category_label}\n\n"
            f"📂 分類を選択してください：",
            view=view,
            mention_author=False
        )
        await message.add_reaction('⏳')

    elif content in ['酒', 'さけ', 'サケ', 'sake']:
        kenpin_category = 'sake'
        category_label = '🍶 献酒'

        log('INFO', '献品受信', {
            'author': str(message.author),
            'category': kenpin_category
        })

        # 献酒: 分類選択から開始（種類選択はスキップ）
        view = BunruiSelectView(kenpin_category, None)
        await message.reply(
            f"{category_label}\n\n"
            f"📂 分類を選択してください：",
            view=view,
            mention_author=False
        )
        await message.add_reaction('⏳')

    else:
        await message.add_reaction('❓')
        await message.reply(
            "「米」または「酒」と投稿してください",
            mention_author=False
        )
        return


if __name__ == "__main__":
    run_with_retry(client, DISCORD_TOKEN, '献品Monitor')
