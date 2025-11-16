#!/usr/bin/env python3
"""
御神導相談Bot
/相談 コマンドで相談を開始し、フォーム形式で情報を収集してNotionに保存
"""

import discord
from discord import app_commands
from discord.ui import Modal, TextInput, Select, View, Button
import os
from datetime import datetime
import json
import requests

# 環境変数読み込み
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

env = load_env_file()
DISCORD_TOKEN = env.get('DISCORD_TOKEN')
NOTION_TOKEN = env.get('NOTION_TOKEN_TASK')  # 既存のNotionトークンを使用
GOSHIN_DB_ID = '2a300160-1818-81e9-9cee-d5d18ae25a06'

# 相談データを一時保存（ユーザーIDをキーにした辞書）
consultation_data = {}

# Discord Bot設定
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 本人情報入力Modal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PersonInfoModal(Modal, title="本人情報入力"):
    name = TextInput(
        label="氏名",
        placeholder="山田太郎",
        required=True,
        max_length=50
    )

    gender = TextInput(
        label="性別（「男性」または「女性」と入力）",
        placeholder="男性",
        required=True,
        max_length=10
    )

    birthdate = TextInput(
        label="生年月日（例: 1990-01-01）",
        placeholder="1990-01-01",
        required=True,
        max_length=10
    )

    address = TextInput(
        label="現住所",
        placeholder="京都市○○区...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # 性別チェック
        if self.gender.value not in ['男性', '女性']:
            await interaction.response.send_message(
                "性別は「男性」または「女性」と入力してください。",
                ephemeral=True
            )
            return

        # データ保存
        consultation_data[user_id] = {
            'name': self.name.value,
            'gender': self.gender.value,
            'birthdate': self.birthdate.value,
            'address': self.address.value,
            'discord_user_id': str(user_id),
            'cohabitants': []
        }

        # 同居人数選択
        await interaction.response.send_message(
            "本人情報を記録しました。\n\n現在、同じ住まいで暮らしている方はいますか？",
            view=CohabitantCountView(),
            ephemeral=True
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 同居人数選択
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CohabitantCountView(View):
    @discord.ui.select(
        placeholder="同居人数を選択してください",
        options=[
            discord.SelectOption(label="0人（一人暮らし）", value="0"),
            discord.SelectOption(label="1人", value="1"),
            discord.SelectOption(label="2人", value="2"),
            discord.SelectOption(label="3人", value="3"),
            discord.SelectOption(label="4人", value="4"),
            discord.SelectOption(label="5人以上", value="5"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        user_id = interaction.user.id
        count = int(select.values[0])

        consultation_data[user_id]['cohabitant_count'] = count
        consultation_data[user_id]['current_cohabitant_index'] = 0

        if count == 0:
            # 同居人なし → 相談種別選択へ
            await interaction.response.send_message(
                "ご相談内容を選択してください",
                view=ConsultationTypeView(),
                ephemeral=True
            )
        else:
            # 同居人情報入力へ
            await interaction.response.send_message(
                f"同居人1人目の情報を入力してください",
                view=CohabitantInfoButton(),
                ephemeral=True
            )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 同居人情報入力
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CohabitantInfoButton(View):
    @discord.ui.button(label="情報を入力", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CohabitantInfoModal())

class CohabitantInfoModal(Modal, title="同居人情報入力"):
    name = TextInput(
        label="氏名",
        placeholder="山田花子",
        required=True,
        max_length=50
    )

    birthdate = TextInput(
        label="生年月日（例: 1995-05-15）",
        placeholder="1995-05-15",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # 一時保存
        consultation_data[user_id]['temp_cohabitant'] = {
            'name': self.name.value,
            'birthdate': self.birthdate.value
        }

        # 続柄選択
        await interaction.response.send_message(
            f"{self.name.value}さんとの続柄を選択してください",
            view=RelationshipSelectView(),
            ephemeral=True
        )

class RelationshipSelectView(View):
    @discord.ui.select(
        placeholder="続柄を選択してください",
        options=[
            discord.SelectOption(label="配偶者", value="配偶者"),
            discord.SelectOption(label="子", value="子"),
            discord.SelectOption(label="父", value="父"),
            discord.SelectOption(label="母", value="母"),
            discord.SelectOption(label="祖父", value="祖父"),
            discord.SelectOption(label="祖母", value="祖母"),
            discord.SelectOption(label="兄弟姉妹", value="兄弟姉妹"),
            discord.SelectOption(label="友人", value="友人"),
            discord.SelectOption(label="その他", value="その他"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        user_id = interaction.user.id
        relationship = select.values[0]

        if relationship == "その他":
            # 自由記述Modal表示
            await interaction.response.send_modal(RelationshipOtherModal())
        else:
            # 続柄確定
            await finalize_cohabitant(interaction, user_id, relationship)

class RelationshipOtherModal(Modal, title="続柄（自由記述）"):
    relationship_text = TextInput(
        label="続柄を入力してください",
        placeholder="例: 義父、叔父、など",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        relationship = self.relationship_text.value
        await finalize_cohabitant(interaction, user_id, relationship)

async def finalize_cohabitant(interaction: discord.Interaction, user_id: int, relationship: str):
    """同居人情報を確定して次へ"""
    temp = consultation_data[user_id]['temp_cohabitant']
    temp['relationship'] = relationship
    consultation_data[user_id]['cohabitants'].append(temp)
    del consultation_data[user_id]['temp_cohabitant']

    current_index = consultation_data[user_id]['current_cohabitant_index']
    total_count = consultation_data[user_id]['cohabitant_count']

    consultation_data[user_id]['current_cohabitant_index'] += 1

    if current_index + 1 < total_count:
        # 次の同居人入力
        await interaction.response.send_message(
            f"同居人{current_index + 2}人目の情報を入力してください",
            view=CohabitantInfoButton(),
            ephemeral=True
        )
    else:
        # 全員入力完了 → 相談種別選択へ
        await interaction.response.send_message(
            "同居人情報を記録しました。\n\nご相談内容を選択してください",
            view=ConsultationTypeView(),
            ephemeral=True
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 相談種別選択
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConsultationTypeView(View):
    @discord.ui.select(
        placeholder="相談内容を選択してください",
        options=[
            discord.SelectOption(label="解体", value="解体"),
            discord.SelectOption(label="新築", value="新築"),
            discord.SelectOption(label="増築", value="増築"),
            discord.SelectOption(label="祖先", value="祖先"),
            discord.SelectOption(label="病気", value="病気"),
            discord.SelectOption(label="仕事", value="仕事"),
            discord.SelectOption(label="就学", value="就学"),
            discord.SelectOption(label="転居", value="転居"),
            discord.SelectOption(label="縁談", value="縁談"),
            discord.SelectOption(label="その他", value="その他"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        user_id = interaction.user.id
        consultation_type = select.values[0]

        consultation_data[user_id]['consultation_type'] = consultation_type

        # 転居の場合のみ追加情報入力
        if consultation_type == "転居":
            await interaction.response.send_message(
                "転居に関する情報を入力してください",
                view=RelocationInfoButton(),
                ephemeral=True
            )
        else:
            # その他の相談は現時点では詳細入力なし → 完了
            await save_to_notion_and_finish(interaction, user_id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 転居固有情報入力
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class RelocationInfoButton(View):
    @discord.ui.button(label="転居情報を入力", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RelocationInfoModal())

class RelocationInfoModal(Modal, title="転居情報入力"):
    new_address = TextInput(
        label="転居先住所",
        placeholder="大阪市○○区...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=200
    )

    relocation_date = TextInput(
        label="転居予定日（例: 2025-12-01）",
        placeholder="2025-12-01",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        consultation_data[user_id]['new_address'] = self.new_address.value
        consultation_data[user_id]['relocation_date'] = self.relocation_date.value

        # Notionに保存して完了
        await save_to_notion_and_finish(interaction, user_id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. Notion保存 & 完了
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_to_notion_and_finish(interaction: discord.Interaction, user_id: int):
    """Notionに保存して相談を完了"""
    data = consultation_data[user_id]

    # 同居人詳細をテキスト化
    cohabitants_text = ""
    for i, cohabitant in enumerate(data['cohabitants'], 1):
        cohabitants_text += f"{i}. {cohabitant['name']} ({cohabitant['relationship']}) - {cohabitant['birthdate']}\n"

    # Notion APIリクエスト
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": {"database_id": GOSHIN_DB_ID},
        "properties": {
            "相談者氏名": {
                "title": [{"text": {"content": data['name']}}]
            },
            "性別": {
                "select": {"name": data['gender']}
            },
            "生年月日": {
                "date": {"start": data['birthdate']}
            },
            "現住所": {
                "rich_text": [{"text": {"content": data['address']}}]
            },
            "相談種別": {
                "select": {"name": data['consultation_type']}
            },
            "相談状況": {
                "select": {"name": "受付"}
            },
            "同居人数": {
                "number": len(data['cohabitants'])
            },
            "同居人詳細": {
                "rich_text": [{"text": {"content": cohabitants_text if cohabitants_text else "なし"}}]
            },
            "DiscordユーザーID": {
                "rich_text": [{"text": {"content": data['discord_user_id']}}]
            }
        }
    }

    # 転居の場合は追加情報
    if data['consultation_type'] == "転居":
        payload["properties"]["転居先住所"] = {
            "rich_text": [{"text": {"content": data.get('new_address', '')}}]
        }
        payload["properties"]["転居予定日"] = {
            "date": {"start": data.get('relocation_date', '')}
        }

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        await interaction.response.send_message(
            "✅ ご相談を受け付けました。\n\n職員から後日ご連絡いたします。",
            ephemeral=True
        )

        # データクリア
        del consultation_data[user_id]

    except Exception as e:
        await interaction.response.send_message(
            f"❌ エラーが発生しました: {str(e)}\n\n恐れ入りますが、直接職員までお問い合わせください。",
            ephemeral=True
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# /相談 コマンド
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tree.command(name="相談", description="御神導の相談を開始します")
async def consultation_command(interaction: discord.Interaction):
    """相談開始コマンド"""
    await interaction.response.send_modal(PersonInfoModal())

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bot起動
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@client.event
async def on_ready():
    await tree.sync()
    print(f'✅ 御神導相談Bot起動: {client.user}')
    print(f'📋 /相談 コマンドが利用可能です')

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
