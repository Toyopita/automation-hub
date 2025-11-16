#!/usr/bin/env python3
"""
Discord ⇒ Notion 記念品発注管理システム

Discordの専用チャンネルの投稿を監視し、
SelectMenuでDB選択、プロジェクト選択、Modalで詳細入力を行います。

機能:
- 2つのDB（祖霊社/本社）から選択
- それぞれのDBに応じたプロジェクト一覧取得
- DB構造に沿った入力フォーム
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List
import discord
from discord import app_commands
from discord.ui import View, Select, Modal, TextInput
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GIFT_CHANNEL_IDS = [
    1435473542006308947   # 記念品発注（IZUMOサーバー）
]

# NotionデータベースID
SORIESHA_GIFT_DB = "1ca00160-1818-8023-b120-ee4dd54fc2c3"  # 祖霊社_記念品発注管理
HONSHA_GIFT_DB = "18800160-1818-804b-9097-cde17e8923fb"    # 本社_記念品発注記録DB
SORIESHA_PROJECT_DB = "1c800160-1818-8004-9609-c1250a7e3478"  # 祖霊社プロジェクトDB
HONSHA_PROJECT_DB = "18d00160-1818-80c6-a1bb-f75325801965"    # プロジェクトDB
VENDOR_DB = "14d00160-1818-800f-a949-f99fefc96065"  # 関係団体DB

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[記念品発注Bot][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


async def get_notion_projects(project_db_id: str, page_size: int = 100) -> List[Dict]:
    """Notionからプロジェクト一覧を取得（完全ページング対応、最大10000件）"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_ORDER")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_ORDERが設定されていません')
            return []

        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }

        projects = []
        has_more = True
        start_cursor = None

        while has_more and len(projects) < 10000:
            payload = {
                "page_size": min(page_size, 100),
                "sorts": [
                    {
                        "property": "期間",
                        "direction": "descending"
                    }
                ]
            }

            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = requests.post(
                f'https://api.notion.com/v1/databases/{project_db_id}/query',
                headers=headers,
                json=payload
            )

            if response.status_code >= 400:
                log('ERROR', 'Notionプロジェクト取得失敗', {'code': response.status_code})
                break

            data = response.json()
            has_more = data.get('has_more', False)
            start_cursor = data.get('next_cursor')

            for page in data.get('results', []):
                project_id = page['id']

                # プロジェクト名を取得（本社DBは「名前」、祖霊社DBは「プロジェクト名」）
                title_prop = page['properties'].get('プロジェクト名') or page['properties'].get('名前')
                if title_prop and title_prop.get('type') == 'title':
                    title_array = title_prop.get('title', [])
                    if title_array:
                        project_name = title_array[0].get('plain_text', '無題')
                    else:
                        project_name = '無題'
                else:
                    project_name = '無題'

                # 期間を取得
                date_prop = page['properties'].get('期間', {})
                date_str = ''
                if date_prop.get('type') == 'date' and date_prop.get('date'):
                    date_obj = date_prop['date']
                    start = date_obj.get('start', '')
                    if start:
                        try:
                            date_str = datetime.strptime(start[:10], '%Y-%m-%d').strftime('%Y/%m/%d')
                        except:
                            date_str = start[:10]

                projects.append({
                    'id': project_id,
                    'name': project_name,
                    'date': date_str
                })

        log('INFO', f'{len(projects)}件のプロジェクトを取得（DB: {project_db_id}）')
        return projects

    except Exception as err:
        log('ERROR', 'プロジェクト取得例外', {'error': str(err)})
        return []


async def get_vendor_list(page_size: int = 100) -> List[Dict]:
    """関係団体DBから記念品タグの団体を取得"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_ORDER")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_ORDERが設定されていません')
            return []

        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }

        vendors = []
        has_more = True
        start_cursor = None

        while has_more and len(vendors) < 10000:
            payload = {
                "page_size": min(page_size, 100),
                "sorts": [
                    {
                        "property": "団体名",
                        "direction": "ascending"
                    }
                ]
            }

            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = requests.post(
                f'https://api.notion.com/v1/databases/{VENDOR_DB}/query',
                headers=headers,
                json=payload
            )

            if response.status_code >= 400:
                log('ERROR', 'Notion発注先取得失敗', {'code': response.status_code})
                break

            data = response.json()
            has_more = data.get('has_more', False)
            start_cursor = data.get('next_cursor')

            for page in data.get('results', []):
                vendor_id = page['id']

                # 団体名を取得
                title_prop = page['properties'].get('団体名')
                if title_prop and title_prop.get('type') == 'title':
                    title_array = title_prop.get('title', [])
                    if title_array:
                        vendor_name = title_array[0].get('plain_text', '無題')
                    else:
                        vendor_name = '無題'
                else:
                    vendor_name = '無題'

                vendors.append({
                    'id': vendor_id,
                    'name': vendor_name
                })

        log('INFO', f'{len(vendors)}件の発注先を取得')
        return vendors

    except Exception as err:
        log('ERROR', '発注先取得例外', {'error': str(err)})
        return []


async def create_soriesha_gift(item_name: str, project_id: str, quantity: int, unit_price: int,
                                delivery_date: str = None, note: str = None, vendor_id: str = None) -> bool:
    """祖霊社_記念品発注管理にエントリ作成"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_ORDER")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_ORDERが設定されていません')
            return False

        properties = {
            "商品名": {
                "title": [{"type": "text", "text": {"content": item_name}}]
            },
            "数量": {
                "number": quantity
            },
            "単価": {
                "number": unit_price
            },
            "プロジェクト名": {
                "relation": [{"id": project_id}]
            }
        }

        if vendor_id:
            properties["発注先"] = {"relation": [{"id": vendor_id}]}

        if delivery_date:
            properties["納品予定日"] = {"date": {"start": delivery_date}}

        if note:
            properties["備考"] = {"rich_text": [{"type": "text", "text": {"content": note}}]}

        payload = {
            "parent": {"database_id": SORIESHA_GIFT_DB},
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
            log('ERROR', 'Notion APIエラー（祖霊社）', {
                'code': response.status_code,
                'message': error_detail.get('message')
            })
            return False
        else:
            log('SUCCESS', 'Notion登録成功（祖霊社）', {
                'item': item_name,
                'quantity': quantity,
                'unit_price': unit_price,
                'project_id': project_id
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外（祖霊社）', {'error': str(err)})
        return False


async def create_honsha_gift(item_name: str, project_id: str, order_quantity: int,
                              carryover: int = 0, proposal_url: str = None) -> bool:
    """本社_記念品発注記録DBにエントリ作成"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_ORDER")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_ORDERが設定されていません')
            return False

        properties = {
            "商品名": {
                "title": [{"type": "text", "text": {"content": item_name}}]
            },
            "発注数": {
                "number": order_quantity
            },
            "プロジェクト名": {
                "relation": [{"id": project_id}]
            }
        }

        if carryover > 0:
            properties["前年からの繰越数"] = {"number": carryover}

        if proposal_url:
            properties["提案書"] = {"files": [{"name": "提案書", "external": {"url": proposal_url}}]}

        payload = {
            "parent": {"database_id": HONSHA_GIFT_DB},
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
            log('ERROR', 'Notion APIエラー（本社）', {
                'code': response.status_code,
                'message': error_detail.get('message')
            })
            return False
        else:
            log('SUCCESS', 'Notion登録成功（本社）', {
                'item': item_name,
                'order_quantity': order_quantity,
                'project_id': project_id
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外（本社）', {'error': str(err)})
        return False


class SorieshaGiftModal(Modal, title="祖霊社 記念品発注入力"):
    """祖霊社_記念品発注管理用Modal"""

    def __init__(self, item_name: str, project_id: str, project_name: str, vendor_id: str = None, vendor_name: str = None):
        super().__init__(timeout=300)
        self.item_name = item_name
        self.project_id = project_id
        self.project_name = project_name
        self.vendor_id = vendor_id
        self.vendor_name = vendor_name

        self.quantity_input = TextInput(
            label="数量",
            placeholder="例: 100",
            required=True,
            max_length=10
        )
        self.add_item(self.quantity_input)

        self.unit_price_input = TextInput(
            label="単価（円）",
            placeholder="例: 500",
            required=True,
            max_length=10
        )
        self.add_item(self.unit_price_input)

        self.delivery_date_input = TextInput(
            label="納品予定日（任意）",
            placeholder="YYYY-MM-DD 形式（例: 2025-11-15）",
            required=False,
            max_length=10
        )
        self.add_item(self.delivery_date_input)

        self.note_input = TextInput(
            label="備考（任意）",
            placeholder="特記事項があれば入力",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        """入力完了時"""
        try:
            quantity = int(str(self.quantity_input.value).strip())
            unit_price = int(str(self.unit_price_input.value).strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ 数量と単価は数値で入力してください。",
                ephemeral=True
            )
            return

        delivery_date = str(self.delivery_date_input.value).strip() if self.delivery_date_input.value else None
        note = str(self.note_input.value).strip() if self.note_input.value else None

        # 納品予定日のバリデーション
        if delivery_date:
            try:
                datetime.strptime(delivery_date, '%Y-%m-%d')
            except ValueError:
                await interaction.response.send_message(
                    "❌ 納品予定日の形式が正しくありません。YYYY-MM-DD 形式で入力してください。",
                    ephemeral=True
                )
                return

        await interaction.response.defer(ephemeral=True)

        success = await create_soriesha_gift(
            self.item_name,
            self.project_id,
            quantity,
            unit_price,
            delivery_date,
            note,
            self.vendor_id
        )

        if success:
            total = quantity * unit_price
            result_msg = (
                f"✅ 祖霊社記念品発注登録完了\n\n"
                f"📝 商品名: {self.item_name}\n"
                f"📁 プロジェクト: {self.project_name}\n"
                f"🔢 数量: {quantity}\n"
                f"💰 単価: ¥{unit_price:,}\n"
                f"💵 合計: ¥{total:,}\n"
            )
            if self.vendor_name:
                result_msg += f"🏢 発注先: {self.vendor_name}\n"
            if delivery_date:
                result_msg += f"📅 納品予定日: {delivery_date}\n"
            if note:
                result_msg += f"📌 備考: {note}\n"

            await interaction.followup.send(result_msg, ephemeral=True)
        else:
            await interaction.followup.send(
                "⚠️ Notion登録に失敗しました。",
                ephemeral=True
            )


class HonshaGiftModal(Modal, title="本社 記念品発注入力"):
    """本社_記念品発注記録DB用Modal"""

    def __init__(self, item_name: str, project_id: str, project_name: str):
        super().__init__(timeout=300)
        self.item_name = item_name
        self.project_id = project_id
        self.project_name = project_name

        self.order_quantity_input = TextInput(
            label="発注数",
            placeholder="例: 200",
            required=True,
            max_length=10
        )
        self.add_item(self.order_quantity_input)

        self.carryover_input = TextInput(
            label="前年からの繰越数（任意）",
            placeholder="例: 50",
            required=False,
            max_length=10
        )
        self.add_item(self.carryover_input)

        self.proposal_url_input = TextInput(
            label="提案書URL（任意）",
            placeholder="https://...",
            required=False,
            max_length=500
        )
        self.add_item(self.proposal_url_input)

    async def on_submit(self, interaction: discord.Interaction):
        """入力完了時"""
        try:
            order_quantity = int(str(self.order_quantity_input.value).strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ 発注数は数値で入力してください。",
                ephemeral=True
            )
            return

        carryover = 0
        if self.carryover_input.value:
            try:
                carryover = int(str(self.carryover_input.value).strip())
            except ValueError:
                await interaction.response.send_message(
                    "❌ 繰越数は数値で入力してください。",
                    ephemeral=True
                )
                return

        proposal_url = str(self.proposal_url_input.value).strip() if self.proposal_url_input.value else None

        await interaction.response.defer(ephemeral=True)

        success = await create_honsha_gift(
            self.item_name,
            self.project_id,
            order_quantity,
            carryover,
            proposal_url
        )

        if success:
            result_msg = (
                f"✅ 本社記念品発注登録完了\n\n"
                f"📝 商品名: {self.item_name}\n"
                f"📁 プロジェクト: {self.project_name}\n"
                f"🔢 発注数: {order_quantity}\n"
            )
            if carryover > 0:
                result_msg += f"📦 繰越数: {carryover}\n"
            if proposal_url:
                result_msg += f"📄 提案書: {proposal_url}\n"

            await interaction.followup.send(result_msg, ephemeral=True)
        else:
            await interaction.followup.send(
                "⚠️ Notion登録に失敗しました。",
                ephemeral=True
            )


class VendorSelect(Select):
    """発注先選択用SelectMenu"""

    def __init__(self, vendors: List[Dict], item_name: str, project_id: str, project_name: str, page: int = 0):
        # ページング: 24件ずつ表示（先頭に「指定しない」オプションがあるため24件）
        start_idx = page * 24
        end_idx = start_idx + 24
        page_vendors = vendors[start_idx:end_idx]

        options = []

        # 最初のページのみ「発注先を指定しない」オプションを追加
        if page == 0:
            options.append(discord.SelectOption(
                label="発注先を指定しない",
                value="none",
                description="発注先を設定せずに登録"
            ))

        for v in page_vendors:
            options.append(discord.SelectOption(
                label=v['name'][:100],
                value=v['id']
            ))

        super().__init__(
            placeholder="発注先を選択してください",
            min_values=1,
            max_values=1,
            options=options
        )
        self.vendors = {v['id']: v['name'] for v in vendors}
        self.item_name = item_name
        self.project_id = project_id
        self.project_name = project_name

    async def callback(self, interaction: discord.Interaction):
        """発注先選択時"""
        vendor_id = self.values[0]

        if vendor_id == "none":
            # 発注先を指定しない場合
            await interaction.response.send_modal(
                SorieshaGiftModal(self.item_name, self.project_id, self.project_name, None, None)
            )
        else:
            # 発注先を指定する場合
            vendor_name = self.vendors.get(vendor_id, '選択発注先')
            await interaction.response.send_modal(
                SorieshaGiftModal(self.item_name, self.project_id, self.project_name, vendor_id, vendor_name)
            )


class VendorSelectView(View):
    """発注先選択View（ページング付き）"""

    def __init__(self, vendors: List[Dict], item_name: str, project_id: str, project_name: str, page: int = 0, timeout=180):
        super().__init__(timeout=timeout)
        self.vendors = vendors
        self.item_name = item_name
        self.project_id = project_id
        self.project_name = project_name
        self.page = page
        self.total_pages = (len(vendors) - 1) // 24 + 1

        # SelectMenuを追加
        self.add_item(VendorSelect(vendors, item_name, project_id, project_name, page))

        # ページングボタンを追加
        if self.total_pages > 1:
            prev_button = discord.ui.Button(
                label="◀ 前へ",
                style=discord.ButtonStyle.gray,
                disabled=(page == 0)
            )
            prev_button.callback = self.prev_page
            self.add_item(prev_button)

            page_button = discord.ui.Button(
                label=f"{page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(page_button)

            next_button = discord.ui.Button(
                label="次へ ▶",
                style=discord.ButtonStyle.gray,
                disabled=(page >= self.total_pages - 1)
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def prev_page(self, interaction: discord.Interaction):
        """前のページへ"""
        new_page = max(0, self.page - 1)
        new_view = VendorSelectView(self.vendors, self.item_name, self.project_id, self.project_name, new_page)
        await interaction.response.edit_message(
            content=f"📝 商品名: **{self.item_name}**\n"
                    f"📁 プロジェクト: **{self.project_name}**\n\n"
                    f"発注先を選択してください（{len(self.vendors)}件中 {new_page * 24 + 1}〜{min((new_page + 1) * 24, len(self.vendors))}件目）：",
            view=new_view
        )

    async def next_page(self, interaction: discord.Interaction):
        """次のページへ"""
        new_page = min(self.total_pages - 1, self.page + 1)
        new_view = VendorSelectView(self.vendors, self.item_name, self.project_id, self.project_name, new_page)
        await interaction.response.edit_message(
            content=f"📝 商品名: **{self.item_name}**\n"
                    f"📁 プロジェクト: **{self.project_name}**\n\n"
                    f"発注先を選択してください（{len(self.vendors)}件中 {new_page * 24 + 1}〜{min((new_page + 1) * 24, len(self.vendors))}件目）：",
            view=new_view
        )


class ProjectSelect(Select):
    """プロジェクト選択用SelectMenu"""

    def __init__(self, projects: List[Dict], item_name: str, db_type: str, page: int = 0):
        # ページング: 25件ずつ表示
        start_idx = page * 25
        end_idx = start_idx + 25
        page_projects = projects[start_idx:end_idx]

        options = []
        for p in page_projects:
            label = p['name'][:80]
            if p.get('date'):
                label = f"{label} ({p['date']})"
            label = label[:100]

            options.append(discord.SelectOption(
                label=label,
                value=p['id'],
                description=p.get('date', '')[:100] if p.get('date') else None
            ))

        super().__init__(
            placeholder="プロジェクトを選択してください",
            min_values=1,
            max_values=1,
            options=options
        )
        self.projects = {p['id']: p['name'] for p in projects}
        self.item_name = item_name
        self.db_type = db_type

    async def callback(self, interaction: discord.Interaction):
        """プロジェクト選択時"""
        project_id = self.values[0]
        project_name = self.projects.get(project_id, '選択プロジェクト')

        if self.db_type == 'soriesha':
            # 祖霊社の場合は発注先選択画面へ
            # 先に発注先リストを取得
            vendors = await get_vendor_list()

            if not vendors:
                # 発注先がない場合は直接Modalへ（発注先なし）
                await interaction.response.send_modal(
                    SorieshaGiftModal(self.item_name, project_id, project_name, None, None)
                )
                return

            # 発注先選択UIを表示
            await interaction.response.defer(ephemeral=True)

            view = VendorSelectView(vendors, self.item_name, project_id, project_name, page=0)
            total_pages = (len(vendors) - 1) // 24 + 1
            page_info = f"1〜{min(24, len(vendors))}件目" if total_pages > 1 else f"{len(vendors)}件"

            await interaction.followup.send(
                f"📝 商品名: **{self.item_name}**\n"
                f"📁 プロジェクト: **{project_name}**\n\n"
                f"発注先を選択してください（{len(vendors)}件中 {page_info}）：",
                view=view,
                ephemeral=True
            )
        else:  # honsha
            await interaction.response.send_modal(
                HonshaGiftModal(self.item_name, project_id, project_name)
            )


class ProjectSelectView(View):
    """プロジェクト選択View（ページング付き）"""

    def __init__(self, projects: List[Dict], item_name: str, db_type: str, page: int = 0, timeout=180):
        super().__init__(timeout=timeout)
        self.projects = projects
        self.item_name = item_name
        self.db_type = db_type
        self.page = page
        self.total_pages = (len(projects) - 1) // 25 + 1

        # SelectMenuを追加
        self.add_item(ProjectSelect(projects, item_name, db_type, page))

        # ページングボタンを追加
        if self.total_pages > 1:
            prev_button = discord.ui.Button(
                label="◀ 前へ",
                style=discord.ButtonStyle.gray,
                disabled=(page == 0)
            )
            prev_button.callback = self.prev_page
            self.add_item(prev_button)

            page_button = discord.ui.Button(
                label=f"{page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(page_button)

            next_button = discord.ui.Button(
                label="次へ ▶",
                style=discord.ButtonStyle.gray,
                disabled=(page >= self.total_pages - 1)
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def prev_page(self, interaction: discord.Interaction):
        """前のページへ"""
        new_page = max(0, self.page - 1)
        new_view = ProjectSelectView(self.projects, self.item_name, self.db_type, new_page)
        await interaction.response.edit_message(
            content=f"📝 商品名: **{self.item_name}**\n\n"
                    f"プロジェクトを選択してください（{len(self.projects)}件中 {new_page * 25 + 1}〜{min((new_page + 1) * 25, len(self.projects))}件目）：",
            view=new_view
        )

    async def next_page(self, interaction: discord.Interaction):
        """次のページへ"""
        new_page = min(self.total_pages - 1, self.page + 1)
        new_view = ProjectSelectView(self.projects, self.item_name, self.db_type, new_page)
        await interaction.response.edit_message(
            content=f"📝 商品名: **{self.item_name}**\n\n"
                    f"プロジェクトを選択してください（{len(self.projects)}件中 {new_page * 25 + 1}〜{min((new_page + 1) * 25, len(self.projects))}件目）：",
            view=new_view
        )


class DatabaseSelect(Select):
    """DB選択用SelectMenu"""

    def __init__(self, item_name: str):
        options = [
            discord.SelectOption(
                label="祖霊社_記念品発注管理",
                value="soriesha",
                description="祖霊社のプロジェクト記念品発注"
            ),
            discord.SelectOption(
                label="本社_記念品発注記録DB",
                value="honsha",
                description="本社のプロジェクト記念品発注"
            )
        ]

        super().__init__(
            placeholder="登録先のデータベースを選択してください",
            min_values=1,
            max_values=1,
            options=options
        )
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        """DB選択時"""
        db_type = self.values[0]

        await interaction.response.defer(ephemeral=True)

        # 選択されたDBに応じてプロジェクト一覧を取得
        if db_type == 'soriesha':
            projects = await get_notion_projects(SORIESHA_PROJECT_DB)
            db_name = "祖霊社_記念品発注管理"
        else:  # honsha
            projects = await get_notion_projects(HONSHA_PROJECT_DB)
            db_name = "本社_記念品発注記録DB"

        if not projects:
            await interaction.followup.send(
                f"❌ {db_name}のプロジェクト取得に失敗しました。",
                ephemeral=True
            )
            return

        # プロジェクト選択UIを表示
        view = ProjectSelectView(projects, self.item_name, db_type, page=0)
        total_pages = (len(projects) - 1) // 25 + 1
        page_info = f"1〜{min(25, len(projects))}件目" if total_pages > 1 else f"{len(projects)}件"

        await interaction.followup.send(
            f"📝 商品名: **{self.item_name}**\n"
            f"📁 登録先: **{db_name}**\n\n"
            f"プロジェクトを選択してください（{len(projects)}件中 {page_info}）：",
            view=view,
            ephemeral=True
        )


class DatabaseSelectView(View):
    """DB選択View"""

    def __init__(self, item_name: str, timeout=180):
        super().__init__(timeout=timeout)
        self.item_name = item_name
        self.add_item(DatabaseSelect(item_name))


@client.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {client.user}')
    log('INFO', f'記念品発注チャンネル監視開始: {GIFT_CHANNEL_IDS}')


@client.event
async def on_message(message: discord.Message):
    """メッセージ受信時"""
    # Botの発言は無視
    if message.author.bot:
        return

    # デバッグ: 全てのメッセージを記録
    log('DEBUG', f'メッセージ受信: チャンネル={message.channel.name} (ID: {message.channel.id}), サーバー={message.guild.name}')

    # 記念品発注チャンネル以外は無視
    if message.channel.id not in GIFT_CHANNEL_IDS:
        return

    item_name = message.content.strip()
    if not item_name:
        await message.add_reaction('❓')
        return

    log('INFO', '記念品発注受信', {
        'author': str(message.author),
        'item': item_name[:100]
    })

    # DB選択UIを表示
    view = DatabaseSelectView(item_name)

    await message.reply(
        f"📝 商品名: **{item_name}**\n\n"
        f"どちらのデータベースに登録しますか？",
        view=view,
        mention_author=False
    )
    await message.add_reaction('⏳')


if __name__ == "__main__":
    log('INFO', '記念品発注監視Bot起動中...')
    client.run(DISCORD_TOKEN)
