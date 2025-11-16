#!/usr/bin/env python3
"""
Discord ⇒ Notion タスクメモ自動登録（テスト版 - UI改善）

Discordの「タスクメモテスト」チャンネルの投稿を監視し、
SelectMenuでプロジェクト選択、Modalで期限入力を行います。
"""

import os
import json
from datetime import datetime, date
from typing import Optional, Dict, List
import discord
from discord import app_commands
from discord.ui import View, Select, Modal, TextInput
from dotenv import load_dotenv
import requests

# 環境変数読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TEST_CHANNEL_ID = 1435453379357966396  # タスクメモテスト
TASK_CHANNEL_ID = 1434168803326951456  # 本番用（既存）
NOTION_TASK_DB_ID = "1c800160-1818-807c-b083-f475eb3a07b9"
NOTION_PROJECT_DB_ID = "1c800160-1818-8004-9609-c1250a7e3478"

# Bot初期化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def log(level: str, message: str, data: Optional[Dict] = None):
    """ログ出力"""
    timestamp = datetime.now().isoformat()
    log_msg = f"[タスクメモTest][{level}] {timestamp} - {message}"
    if data:
        log_msg += f" | {json.dumps(data, ensure_ascii=False)}"
    print(log_msg)


async def get_notion_projects(page_size: int = 100) -> List[Dict]:
    """Notionから未完了プロジェクト一覧を取得（ページング対応）"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_TASK")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_TASKが設定されていません')
            return []

        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }

        # 未完了プロジェクトを取得（完了ステータスを除外）
        payload = {
            "page_size": page_size,
            "sorts": [
                {
                    "property": "期間",
                    "direction": "descending"
                }
            ]
        }

        response = requests.post(
            f'https://api.notion.com/v1/databases/{NOTION_PROJECT_DB_ID}/query',
            headers=headers,
            json=payload
        )

        if response.status_code >= 400:
            log('ERROR', 'Notionプロジェクト取得失敗', {'code': response.status_code})
            return []

        data = response.json()
        projects = []

        for page in data.get('results', []):
            project_id = page['id']

            # プロジェクト名を取得
            title_prop = page['properties'].get('プロジェクト名', {})
            if title_prop.get('type') == 'title':
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
                    # YYYY-MM-DD形式から YYYY/MM/DD に変換
                    try:
                        date_str = datetime.strptime(start[:10], '%Y-%m-%d').strftime('%Y/%m/%d')
                    except:
                        date_str = start[:10]

            # 全てのプロジェクトを取得（完了も含む）
            projects.append({
                'id': project_id,
                'name': project_name,
                'date': date_str
            })

        log('INFO', f'{len(projects)}件のプロジェクトを取得')
        return projects

    except Exception as err:
        log('ERROR', 'プロジェクト取得例外', {'error': str(err)})
        return []


async def create_notion_task(task_name: str, project_id: str, due_date: str) -> bool:
    """Notionにタスクを作成"""
    try:
        notion_token = os.getenv("NOTION_TOKEN_TASK")
        if not notion_token:
            log('ERROR', 'NOTION_TOKEN_TASKが設定されていません')
            return False

        properties = {
            "タスク名": {
                "title": [{
                    "type": "text",
                    "text": {"content": task_name}
                }]
            },
            "期限": {
                "date": {"start": due_date}
            },
            "プロジェクト名": {
                "relation": [{"id": project_id}]
            }
        }

        payload = {
            "parent": {"database_id": NOTION_TASK_DB_ID},
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
                'task': task_name,
                'deadline': due_date,
                'project_id': project_id
            })
            return True

    except Exception as err:
        log('ERROR', 'Notion登録例外', {'error': str(err)})
        return False


class DueDateModal(Modal, title="期限を入力"):
    """期限入力用Modal（複数タスク対応）"""

    def __init__(self, task_names: List[str], project_id: str, project_name: str):
        super().__init__(timeout=300)
        self.task_names = task_names
        self.project_id = project_id
        self.project_name = project_name

        self.date_input = TextInput(
            label="期限（日付）",
            placeholder="YYYY-MM-DD 形式（例: 2025-11-15）",
            required=True,
            min_length=10,
            max_length=10
        )
        self.add_item(self.date_input)

    async def on_submit(self, interaction: discord.Interaction):
        """期限入力完了時"""
        due_date = str(self.date_input.value).strip()

        # 簡易バリデーション
        try:
            datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            await interaction.response.send_message(
                "❌ 日付形式が正しくありません。YYYY-MM-DD 形式で入力してください。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        # 複数タスクを一括登録
        success_count = 0
        failed_count = 0

        for task_name in self.task_names:
            success = await create_notion_task(task_name, self.project_id, due_date)
            if success:
                success_count += 1
            else:
                failed_count += 1

        # 結果を報告
        if failed_count == 0:
            task_list = '\n'.join([f"  • {name}" for name in self.task_names])
            await interaction.followup.send(
                f"✅ タスク一括登録完了（{success_count}件）\n"
                f"📝 タスク:\n{task_list}\n"
                f"📁 プロジェクト: {self.project_name}\n"
                f"📅 期限: {due_date}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"⚠️ タスク登録完了: {success_count}件成功、{failed_count}件失敗",
                ephemeral=True
            )


class ProjectSelect(Select):
    """プロジェクト選択用SelectMenu（複数タスク対応）"""

    def __init__(self, projects: List[Dict], task_names: List[str], page: int = 0):
        # ページング: 25件ずつ表示
        start_idx = page * 25
        end_idx = start_idx + 25
        page_projects = projects[start_idx:end_idx]

        options = []
        for p in page_projects:
            # 期間がある場合は表示
            label = p['name'][:80]  # 名前は80文字まで
            if p.get('date'):
                label = f"{label} ({p['date']})"
            label = label[:100]  # 最大100文字

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
        self.task_names = task_names

    async def callback(self, interaction: discord.Interaction):
        """プロジェクト選択時"""
        project_id = self.values[0]
        project_name = self.projects.get(project_id, '選択プロジェクト')

        # 期限入力Modalを表示
        await interaction.response.send_modal(
            DueDateModal(self.task_names, project_id, project_name)
        )


class ProjectSelectView(View):
    """プロジェクト選択View（ページング付き・複数タスク対応）"""

    def __init__(self, projects: List[Dict], task_names: List[str], page: int = 0, timeout=180):
        super().__init__(timeout=timeout)
        self.projects = projects
        self.task_names = task_names
        self.page = page
        self.total_pages = (len(projects) - 1) // 25 + 1

        # SelectMenuを追加
        self.add_item(ProjectSelect(projects, task_names, page))

        # ページングボタンを追加（ページが複数ある場合）
        if self.total_pages > 1:
            # 前へボタン
            prev_button = discord.ui.Button(
                label="◀ 前へ",
                style=discord.ButtonStyle.gray,
                disabled=(page == 0)
            )
            prev_button.callback = self.prev_page
            self.add_item(prev_button)

            # ページ表示
            page_button = discord.ui.Button(
                label=f"{page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True
            )
            self.add_item(page_button)

            # 次へボタン
            next_button = discord.ui.Button(
                label="次へ ▶",
                style=discord.ButtonStyle.gray,
                disabled=(page >= self.total_pages - 1)
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    def _format_task_display(self) -> str:
        """タスク名の表示形式を生成"""
        if len(self.task_names) == 1:
            return f"📝 タスク: **{self.task_names[0]}**"
        else:
            task_list = '\n'.join([f"  • {name}" for name in self.task_names])
            return f"📝 タスク（{len(self.task_names)}件）:\n{task_list}"

    async def prev_page(self, interaction: discord.Interaction):
        """前のページへ"""
        new_page = max(0, self.page - 1)
        new_view = ProjectSelectView(self.projects, self.task_names, new_page)
        await interaction.response.edit_message(
            content=f"{self._format_task_display()}\n\n"
                    f"プロジェクトを選択してください（{len(self.projects)}件中 {new_page * 25 + 1}〜{min((new_page + 1) * 25, len(self.projects))}件目）：",
            view=new_view
        )

    async def next_page(self, interaction: discord.Interaction):
        """次のページへ"""
        new_page = min(self.total_pages - 1, self.page + 1)
        new_view = ProjectSelectView(self.projects, self.task_names, new_page)
        await interaction.response.edit_message(
            content=f"{self._format_task_display()}\n\n"
                    f"プロジェクトを選択してください（{len(self.projects)}件中 {new_page * 25 + 1}〜{min((new_page + 1) * 25, len(self.projects))}件目）：",
            view=new_view
        )


@client.event
async def on_ready():
    """Bot起動時"""
    log('INFO', f'Bot起動: {client.user}')
    log('INFO', f'タスクメモテストチャンネル監視開始: {TEST_CHANNEL_ID}')


@client.event
async def on_message(message: discord.Message):
    """メッセージ受信時（改行・カンマ区切りで複数タスク対応）"""
    # Botの発言は無視
    if message.author.bot:
        return

    # タスクメモテストチャンネル以外は無視
    if message.channel.id != TEST_CHANNEL_ID:
        return

    message_text = message.content.strip()
    if not message_text:
        await message.add_reaction('❓')
        return

    # 改行または、（カンマ）で分割してタスク名リストを作成（空行は除外）
    # まず改行で分割
    lines = message_text.split('\n')
    task_names = []
    for line in lines:
        # 各行を、（カンマ）でさらに分割
        parts = line.split('、')
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                task_names.append(cleaned)

    if not task_names:
        await message.add_reaction('❓')
        return

    log('INFO', 'タスクメモ受信', {
        'author': str(message.author),
        'task_count': len(task_names),
        'content': message_text[:100]
    })

    # プロジェクト一覧を取得
    projects = await get_notion_projects()

    if not projects:
        await message.reply(
            "❌ プロジェクトの取得に失敗しました。",
            mention_author=False
        )
        await message.add_reaction('❌')
        return

    # プロジェクト選択UIを表示
    view = ProjectSelectView(projects, task_names, page=0)
    total_pages = (len(projects) - 1) // 25 + 1
    page_info = f"1〜{min(25, len(projects))}件目" if total_pages > 1 else f"{len(projects)}件"

    # タスク名の表示形式
    if len(task_names) == 1:
        task_display = f"📝 タスク: **{task_names[0]}**"
    else:
        task_list = '\n'.join([f"  • {name}" for name in task_names])
        task_display = f"📝 タスク（{len(task_names)}件）:\n{task_list}"

    await message.reply(
        f"{task_display}\n\n"
        f"プロジェクトを選択してください（{len(projects)}件中 {page_info}）：",
        view=view,
        mention_author=False
    )
    await message.add_reaction('⏳')


if __name__ == "__main__":
    log('INFO', 'タスクメモ監視Bot（テスト版）起動中...')
    client.run(DISCORD_TOKEN)
