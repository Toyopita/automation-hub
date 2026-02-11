#!/usr/bin/env python3
"""
LINE ↔ Discord 翻訳Bot（汎用テンプレート版）

設定ファイル（JSON）で対象人物をカスタマイズ可能。
Laura用Bot (laura_line_bot.py) とは完全独立で動作。

使い方:
  python3 line_bot_template.py --config person_config.json

必要な.env変数（config内のenv設定に対応）:
  LINE_PERSON_CHANNEL_SECRET, LINE_PERSON_ACCESS_TOKEN,
  DISCORD_TOKEN_PERSON, PERSON_DISCORD_CHANNEL_ID
"""

import os
import io
import json
import hashlib
import hmac
import base64
import asyncio
import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from collections import deque

import discord
from discord import ui, Embed, ButtonStyle
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import httpx
from chat_logger import log_message, log_media

# ============================================================
# ロギング設定
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('line_bot_template')

# ============================================================
# 環境変数読み込み
# ============================================================
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env()

# ============================================================
# 設定ファイル読み込み
# ============================================================
def load_config(config_path: str) -> dict:
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)

    required = ['name', 'display_name', 'languages', 'timezone', 'port', 'env']
    for key in required:
        if key not in config:
            raise ValueError(f"Config missing required key: {key}")

    env_keys = ['line_channel_secret', 'line_access_token', 'discord_token', 'discord_channel_id']
    for key in env_keys:
        if key not in config['env']:
            raise ValueError(f"Config env missing required key: {key}")

    return config


# ============================================================
# グローバル（configロード後に設定）
# ============================================================
CONFIG: dict = {}
LINE_CHANNEL_SECRET = ''
LINE_ACCESS_TOKEN = ''
DISCORD_TOKEN = ''
CHANNEL_ID = 0
PERSON_TZ = None
PORT = 8788
CLAUDE_CLI = '/Users/minamitakeshi/.local/bin/claude'
CLAUDE_MODEL = 'claude-sonnet-4-5-20250929'
LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'
LINE_CONTENT_URL = 'https://api-data.line.me/v2/bot/message/{message_id}/content'
JST = ZoneInfo('Asia/Tokyo')

# データファイル（name依存、init_globals()で設定）
EMOTION_DATA_FILE: Path = None
PENDING_TRIGGERS_FILE: Path = None
CONV_BUFFER_FILE: Path = None
USER_ID_FILE: Path = None

# LINE User ID（初回メッセージで自動取得）
line_user_id = None

# 翻訳プロンプト（init_globals()で設定）
TRANSLATE_INCOMING_PROMPT = ''
TRANSLATE_OUTGOING_PROMPT = ''

# 会話コンテキストバッファ
CONV_BUFFER_MAX = 20
conversation_buffer: deque = deque(maxlen=CONV_BUFFER_MAX)


def init_globals(config: dict):
    """configからグローバル変数を初期化"""
    global CONFIG, LINE_CHANNEL_SECRET, LINE_ACCESS_TOKEN, DISCORD_TOKEN
    global CHANNEL_ID, PERSON_TZ, PORT, CLAUDE_MODEL
    global EMOTION_DATA_FILE, PENDING_TRIGGERS_FILE, CONV_BUFFER_FILE, USER_ID_FILE
    global TRANSLATE_INCOMING_PROMPT, TRANSLATE_OUTGOING_PROMPT

    CONFIG = config
    name = config['name'].lower()
    env = config['env']

    LINE_CHANNEL_SECRET = os.environ[env['line_channel_secret']]
    LINE_ACCESS_TOKEN = os.environ[env['line_access_token']]
    DISCORD_TOKEN = os.environ[env['discord_token']]
    CHANNEL_ID = int(os.environ[env['discord_channel_id']])
    PERSON_TZ = ZoneInfo(config['timezone'])
    PORT = config.get('port', 8788)
    CLAUDE_MODEL = config.get('claude_model', 'claude-sonnet-4-5-20250929')

    base_dir = Path(__file__).parent
    EMOTION_DATA_FILE = base_dir / f'{name}_emotion_data.json'
    PENDING_TRIGGERS_FILE = base_dir / f'.{name}_pending_triggers.json'
    CONV_BUFFER_FILE = base_dir / f'.{name}_conversation_buffer.json'
    USER_ID_FILE = base_dir / f'.{name}_line_user_id'

    # プロンプト読み込み（カスタムファイル or デフォルト生成）
    TRANSLATE_INCOMING_PROMPT = _load_or_generate_incoming_prompt(config)
    TRANSLATE_OUTGOING_PROMPT = _load_or_generate_outgoing_prompt(config)

    # LINE User ID 復元
    _load_user_id()

    # 会話バッファ復元
    _load_conversation_buffer()

    logger.info(f"Config loaded: {config['display_name']} ({name})")
    logger.info(f"Port: {PORT}, TZ: {config['timezone']}, Channel: {CHANNEL_ID}")


# ============================================================
# プロンプト生成
# ============================================================
def _load_prompt_file(path_str) -> str | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = Path(__file__).parent / p
    if p.exists():
        return p.read_text(encoding='utf-8')
    return None


def _load_or_generate_incoming_prompt(config: dict) -> str:
    """受信翻訳プロンプト（相手→日本語）"""
    custom = _load_prompt_file(config.get('prompt_incoming_file'))
    if custom:
        return custom

    name = config['display_name']
    langs = config.get('languages', 'English')
    bg = config.get('background', '')
    rel = config.get('relationship', 'friend')
    tone = config.get('relationship_tone', 'casual')
    emotion = config.get('emotion_analysis', True)

    emotion_section = ""
    if emotion:
        emotion_section = """Also analyze their emotional state.

Return ONLY valid JSON (no markdown, no code blocks, no explanation):
{
  "translation": "日本語訳",
  "scores": {
    "mood": <1-10>,
    "energy": <1-10>,
    "intimacy": <1-10>,
    "longing": <1-10>,
    "eros": <1-10>,
    "ds": <1-10>,
    "playfulness": <1-10>,
    "future": <1-10>,
    "engagement": <1-10>
  },
  "attachment": "safe|anxious|avoidant",
  "risk": "none|minor|caution|danger",
  "language_mix": "en|other|mixed",
  "note": "短い補足コメント（日本語）"
}

Scoring guide:
- mood: 1=negative, 10=positive
- energy: 1=calm, 10=excited
- intimacy: 1=surface level, 10=deep emotional sharing
- longing: 1=neutral, 10=intense missing/wanting/sweetness
- eros: 1=platonic, 10=explicit
- ds: 1=equal dynamic, 10=clear submission
- playfulness: 1=serious, 10=joking/teasing
- future: 1=present talk only, 10=concrete future plans
- engagement: 1=minimal response, 10=actively engaging"""
    else:
        emotion_section = """Return ONLY valid JSON (no markdown, no code blocks, no explanation):
{
  "translation": "日本語訳"
}"""

    return f"""You are a translator for messages between {name} ({langs} speaker. {bg}) and a Japanese person.
Their relationship: {rel}. Tone: {tone}.

Translate {name}'s message to natural Japanese. {emotion_section}

Rules:
- Use {tone} tone appropriate for their {rel} relationship
- Keep translation natural, not textbook Japanese
- If non-English words appear, translate them and note in "note" field"""


def _load_or_generate_outgoing_prompt(config: dict) -> str:
    """送信翻訳プロンプト（日本語→相手の言語）"""
    custom = _load_prompt_file(config.get('prompt_outgoing_file'))
    if custom:
        return custom

    name = config['display_name']
    langs = config.get('languages', 'English')
    rel = config.get('relationship', 'friend')
    tone = config.get('relationship_tone', 'casual')
    n_candidates = config.get('translation_candidates', 5)

    return f"""You are a translator. Translate the Japanese message to natural {langs} for sending to {name}.
Their relationship: {rel}. Tone should be {tone}.

Provide exactly {n_candidates} different translation candidates, each with a different tone/nuance.

Return ONLY valid JSON (no markdown, no code blocks, no explanation):
{{"translations":[{{"text":"translated text","ja":"この英文の自然な日本語訳","nuance":"ニュアンス説明（日本語10-20字）"}}],"category":"affection|interest|daily|humor|sexual|future|support|praise|vulnerable|sensory","modifiers":[]}}

Rules:
- All {n_candidates} candidates must convey the SAME meaning, just with different tone/style
- Use natural, conversational {langs} (not textbook)
- Tone: {tone}
- Modifiers (if applicable): +spontaneous, +callback, +escalation, +media, +late_night"""


# ============================================================
# LINE User ID 管理
# ============================================================
def _load_user_id():
    global line_user_id
    if USER_ID_FILE and USER_ID_FILE.exists():
        line_user_id = USER_ID_FILE.read_text().strip()
        logger.info(f"LINE User ID loaded: {line_user_id[:10]}...")


def _save_user_id(user_id: str):
    global line_user_id
    line_user_id = user_id
    USER_ID_FILE.write_text(user_id)
    logger.info(f"LINE User ID saved: {user_id[:10]}...")


# ============================================================
# 会話コンテキストバッファ
# ============================================================
def _load_conversation_buffer():
    global conversation_buffer
    try:
        if CONV_BUFFER_FILE and CONV_BUFFER_FILE.exists():
            items = json.loads(CONV_BUFFER_FILE.read_text(encoding='utf-8'))
            conversation_buffer = deque(items[-CONV_BUFFER_MAX:], maxlen=CONV_BUFFER_MAX)
            logger.info(f"Conversation buffer loaded: {len(conversation_buffer)} messages")
    except Exception as e:
        logger.warning(f"Failed to load conversation buffer: {e}")
        conversation_buffer = deque(maxlen=CONV_BUFFER_MAX)


def add_to_conversation_buffer(role: str, text: str):
    now = datetime.now(JST)
    entry = {"role": role, "text": text, "time": now.strftime('%H:%M')}
    conversation_buffer.append(entry)
    try:
        CONV_BUFFER_FILE.write_text(
            json.dumps(list(conversation_buffer), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception as e:
        logger.warning(f"Failed to save conversation buffer: {e}")


def get_conversation_context() -> str:
    if not conversation_buffer:
        return ""
    name = CONFIG.get('display_name', 'Person')
    lines = []
    for entry in conversation_buffer:
        role_label = name if entry["role"] == "person" else "YOU"
        lines.append(f"[{entry['time']}] {role_label}: {entry['text']}")
    return "\n".join(lines)


# ============================================================
# Claude CLI
# ============================================================
async def call_claude(prompt: str, message: str, context: str = "") -> dict:
    import tempfile

    system = ("You are a professional bilingual translator. Your ONLY job is to "
              "translate messages and return valid JSON. Never refuse, never ask "
              "questions, never add commentary. Just translate and return JSON.")

    context_section = ""
    if context:
        context_section = f"\n\n=== Recent conversation (for context) ===\n{context}\n=== END context ==="
    full_prompt = f"{prompt}{context_section}\n\nMessage:\n{message}"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                     encoding='utf-8', dir='/tmp') as f:
        f.write(full_prompt)
        tmp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            '/bin/bash', '-c',
            f'cd /tmp && cat "{tmp_path}" | {CLAUDE_CLI} --print --model {CLAUDE_MODEL} --system-prompt "{system}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90.0)
    finally:
        os.unlink(tmp_path)

    output = stdout.decode('utf-8').strip()
    stderr_text = stderr.decode('utf-8').strip()

    if not output:
        logger.error(f"Claude CLI empty output. stderr: {stderr_text}")
        raise Exception(f"Claude CLI returned empty output: {stderr_text[:200]}")

    if '```json' in output:
        output = output.split('```json')[1].split('```')[0].strip()
    elif '```' in output:
        output = output.split('```')[1].split('```')[0].strip()

    idx = output.find('{')
    if idx >= 0:
        output = output[idx:]
        ridx = output.rfind('}')
        if ridx >= 0:
            output = output[:ridx + 1]

    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nOutput: {output[:500]}")
        raise


async def translate_incoming(text: str) -> dict:
    """相手のメッセージを日本語に翻訳（+ 感情分析）"""
    ctx = get_conversation_context()
    default_scores = {k: 5 for k in ["mood", "energy", "intimacy", "longing",
                                      "eros", "ds", "playfulness", "future", "engagement"]}
    last_error = None
    for attempt in range(3):
        try:
            result = await call_claude(TRANSLATE_INCOMING_PROMPT, text, context=ctx)
            translation = result.get("translation", "")
            if translation and translation != text and not translation.startswith("["):
                # 感情分析がない場合のデフォルト補完
                if "scores" not in result:
                    result["scores"] = default_scores
                    result.setdefault("attachment", "safe")
                    result.setdefault("risk", "none")
                    result.setdefault("language_mix", "en")
                    result.setdefault("note", "")
                return result
            logger.warning(f"Translation returned original/empty, retry {attempt + 1}/3")
            last_error = "translation was empty or same as original"
        except Exception as e:
            logger.error(f"Translation error (attempt {attempt + 1}/3): {e}")
            last_error = str(e)
        if attempt < 2:
            await asyncio.sleep(2)

    logger.error(f"All 3 translation attempts failed: {last_error}")
    return {
        "translation": f"[翻訳エラー・原文] {text}",
        "scores": default_scores,
        "attachment": "safe", "risk": "none",
        "language_mix": "en", "note": f"3回リトライ失敗: {last_error}"
    }


async def translate_outgoing(text: str) -> dict:
    """ユーザーの日本語を相手の言語に翻訳"""
    now = datetime.now(JST)
    extra = ""
    if 23 <= now.hour or now.hour < 5:
        extra = "\nNote: Sent late at night (Japan time). Consider +late_night modifier."
    ctx = get_conversation_context()
    last_error = None
    for attempt in range(3):
        try:
            result = await call_claude(TRANSLATE_OUTGOING_PROMPT + extra, text, context=ctx)
            translations = result.get("translations", [])
            if translations and translations[0].get("text", "").strip():
                return result
            logger.warning(f"Outgoing translation returned empty, retry {attempt + 1}/3")
            last_error = "translations empty"
        except Exception as e:
            logger.error(f"Outgoing translation error (attempt {attempt + 1}/3): {e}")
            last_error = str(e)
        if attempt < 2:
            await asyncio.sleep(2)

    logger.error(f"All 3 outgoing translation attempts failed: {last_error}")
    return {
        "translations": [{"text": f"[Translation Error] {text}", "ja": text, "nuance": "翻訳エラー"}],
        "category": "daily", "modifiers": []
    }


# ============================================================
# 感情分析フォーマット
# ============================================================
def format_emotion_bars(scores: dict) -> str:
    labels = [
        ("mood", "気分　　　"), ("energy", "テンション"),
        ("intimacy", "親密度　　"), ("longing", "甘え　　　"),
        ("eros", "エロス　　"), ("ds", "M度　　　"),
        ("playfulness", "遊び心　　"), ("future", "将来　　　"),
        ("engagement", "エンゲージ"),
    ]
    lines = []
    for key, label in labels:
        val = scores.get(key, 5)
        bar = "█" * val + "░" * (10 - val)
        lines.append(f"{label} {bar} {val}")
    return "\n".join(lines)


def format_attachment_risk(attachment: str, risk: str, language_mix: str) -> str:
    att_map = {"safe": "🟢安全", "anxious": "🟡不安", "avoidant": "🔴回避"}
    lang_map = {"en": "🇬🇧", "es": "🇪🇸", "es_en": "🇪🇸🇬🇧",
                "other": "🌐", "mixed": "🌐🇬🇧"}
    return (f"愛着: {att_map.get(attachment, attachment)}  "
            f"危険信号: {risk}  "
            f"言語: {lang_map.get(language_mix, language_mix)}")


# ============================================================
# LINE API ヘルパー
# ============================================================
async def verify_signature(body: bytes, signature: str) -> bool:
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'), body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(expected, signature)


async def send_line_message(user_id: str, text: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINE_PUSH_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
            },
            json={'to': user_id, 'messages': [{'type': 'text', 'text': text}]}
        )
        if response.status_code != 200:
            logger.error(f"LINE Push error: {response.status_code} {response.text}")
            raise Exception(f"LINE API error: {response.status_code}")
        logger.info(f"LINE message sent to {user_id[:10]}...")


async def download_line_content(message_id: str) -> tuple[bytes, str]:
    url = LINE_CONTENT_URL.format(message_id=message_id)
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(
            url, headers={'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'}
        )
        if response.status_code != 200:
            raise Exception(f"LINE Content API error: {response.status_code}")
        content_type = response.headers.get('content-type', '')
        return response.content, content_type


# ============================================================
# 感情データ記録
# ============================================================
def _load_entries() -> list:
    if not EMOTION_DATA_FILE.exists():
        return []
    try:
        with open(EMOTION_DATA_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("entries", [])
        return []
    except Exception:
        return []


def _save_entries(entries: list):
    with open(EMOTION_DATA_FILE, 'w') as f:
        json.dump({"version": 2, "entries": entries}, f, ensure_ascii=False, indent=2)


async def log_emotion_data(message: str, analysis: dict, trigger: dict = None):
    if not CONFIG.get('emotion_analysis', True):
        return None

    now = datetime.now(JST)
    entries = _load_entries()

    prev_scores = None
    score_deltas = None
    if entries:
        prev_scores = entries[-1].get("scores")
        if prev_scores and "scores" in analysis:
            score_deltas = {
                k: analysis["scores"][k] - prev_scores.get(k, 5)
                for k in analysis["scores"]
            }

    entry = {
        "timestamp": now.isoformat(),
        "summary": message[:100],
        "scores": analysis.get("scores", {}),
        "attachment": analysis.get("attachment", "safe"),
        "risk": analysis.get("risk", "none"),
        "language_mix": analysis.get("language_mix", "en"),
        "note": analysis.get("note", ""),
        "trigger": trigger,
        "prev_scores": prev_scores,
        "score_deltas": score_deltas
    }
    entries.append(entry)
    _save_entries(entries)
    logger.info("Emotion data logged")
    return entry


# ============================================================
# Discord Bot
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

discord_client = discord.Client(intents=intents)
discord_ready = asyncio.Event()


class SendConfirmView(ui.View):
    """翻訳候補から選択して送信"""
    def __init__(self, candidates: list, japanese_text: str, category: str, modifiers: list):
        super().__init__(timeout=300)
        self.candidates = candidates
        self.japanese_text = japanese_text
        self.category = category
        self.modifiers = modifiers
        self.selected_index = None

        options = []
        for i, c in enumerate(candidates):
            num = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'][i] if i < 5 else str(i + 1)
            ja = c.get('ja', '')
            desc = f"{ja[:50]} | {c.get('nuance', '')}"[:100]
            options.append(discord.SelectOption(
                label=f"{num} {c['text'][:93]}",
                description=desc, value=str(i)
            ))
        select = ui.Select(placeholder="翻訳候補を選択...", options=options, row=0)
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        self.selected_index = int(interaction.data['values'][0])
        selected = self.candidates[self.selected_index]
        num = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'][self.selected_index]

        embed = Embed(title=f"{num} を選択中", color=0x2ecc71)
        embed.add_field(name="🇯🇵 あなた", value=self.japanese_text, inline=False)
        embed.add_field(
            name="🇬🇧 選択した翻訳",
            value=f"**{selected['text']}**\n> 🇯🇵 {selected.get('ja', '')}\n> _{selected.get('nuance', '')}_",
            inline=False
        )
        embed.add_field(
            name="🏷️", value=f"{self.category} {' '.join(self.modifiers)}", inline=False
        )
        await interaction.response.edit_message(embed=embed)

    @ui.button(label='✅ 送信', style=ButtonStyle.green, row=1)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if self.selected_index is None:
            await interaction.response.send_message("先に候補を選択してください", ephemeral=True)
            return
        if not line_user_id:
            await interaction.response.send_message(
                f"❌ {CONFIG['display_name']}のLINE IDが未取得です（最初のメッセージ待ち）",
                ephemeral=True
            )
            return

        selected = self.candidates[self.selected_index]
        english_text = selected['text']

        try:
            await send_line_message(line_user_id, english_text)

            now = datetime.now(JST)
            now_remote = now.astimezone(PERSON_TZ)
            tz_label = CONFIG.get('timezone_label', 'TZ')

            embed = Embed(
                description=(
                    f"**✅ {CONFIG['display_name']}に送信しました** "
                    f"[{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {tz_label}]\n\n"
                    f"🇯🇵 {self.japanese_text}\n"
                    f"🇬🇧 {english_text}\n"
                    f"> _{selected.get('nuance', '')}_\n\n"
                    f"🏷️ {self.category} {' '.join(self.modifiers)}"
                ),
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)

            trigger = {
                "message": english_text,
                "sent_at": now.isoformat(),
                "category": self.category,
                "modifiers": self.modifiers
            }
            triggers = []
            if PENDING_TRIGGERS_FILE.exists():
                try:
                    triggers = json.loads(PENDING_TRIGGERS_FILE.read_text())
                except Exception:
                    triggers = []
            triggers.append(trigger)
            PENDING_TRIGGERS_FILE.write_text(json.dumps(triggers, ensure_ascii=False, indent=2))

            add_to_conversation_buffer("you", english_text)

            # 会話ログ保存
            log_message(CONFIG['display_name'], "OUT", english_text, original=self.japanese_text)

            logger.info(f"Sent to {CONFIG['display_name']}: {english_text[:50]}...")

        except Exception as e:
            await interaction.response.send_message(f"❌ 送信エラー: {e}", ephemeral=True)

    @ui.button(label='❌ キャンセル', style=ButtonStyle.grey, row=1)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        embed = Embed(description="❌ 送信キャンセル", color=0xff0000)
        await interaction.response.edit_message(embed=embed, view=None)


@discord_client.event
async def on_ready():
    logger.info(f"Discord bot ready: {discord_client.user}")
    discord_ready.set()


@discord_client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.channel.id != CHANNEL_ID:
        return

    text = message.content.strip()
    if not text:
        return
    if text[0] in ('/', '#', '!'):
        return

    async with message.channel.typing():
        result = await translate_outgoing(text)

    candidates = result.get("translations", [])
    category = result.get("category", "daily")
    modifiers = result.get("modifiers", [])

    nums = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
    lines = [f"🇯🇵 **あなた:** {text}\n"]
    for i, c in enumerate(candidates):
        num = nums[i] if i < 5 else str(i + 1)
        ja = c.get('ja', '')
        nuance = c.get('nuance', '')
        lines.append(f"{num} {c['text']}\n> 🇯🇵 {ja}\n> _{nuance}_")
    lines.append(f"\n🏷️ {category} {' '.join(modifiers)}")

    embed = Embed(
        title="✏️ 翻訳プレビュー（候補を選択）",
        description="\n\n".join(lines),
        color=0x3498db
    )
    view = SendConfirmView(candidates, text, category, modifiers)
    await message.reply(embed=embed, view=view)


# ============================================================
# FastAPI (LINE Webhook)
# ============================================================
app = FastAPI()


@app.post("/callback")
async def line_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not await verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(body)
    events = data.get("events", [])

    for event in events:
        event_type = event.get("type", "")
        if event_type == "message":
            msg_type = event["message"]["type"]
            if msg_type == "text":
                asyncio.create_task(handle_line_text(event))
            elif msg_type in ("image", "video"):
                asyncio.create_task(handle_line_media(event))
        elif event_type == "follow":
            user_id = event["source"]["userId"]
            _save_user_id(user_id)

    return {"status": "ok"}


async def handle_line_text(event: dict):
    user_id = event["source"]["userId"]
    text = event["message"]["text"]

    if not line_user_id:
        _save_user_id(user_id)

    logger.info(f"LINE message: {text[:50]}...")
    add_to_conversation_buffer("person", text)

    analysis = await translate_incoming(text)

    # 会話ログ保存
    log_message(CONFIG['display_name'], "IN", analysis.get("translation", text), original=text)

    now = datetime.now(JST)
    now_remote = now.astimezone(PERSON_TZ)
    tz_label = CONFIG.get('timezone_label', 'TZ')
    time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {tz_label}"

    emotion_bars = format_emotion_bars(analysis["scores"])
    att_risk = format_attachment_risk(
        analysis["attachment"], analysis["risk"], analysis["language_mix"]
    )

    # pending trigger
    trigger = None
    if PENDING_TRIGGERS_FILE.exists():
        try:
            triggers = json.loads(PENDING_TRIGGERS_FILE.read_text())
            if triggers:
                trigger = triggers[-1]
                sent_at = datetime.fromisoformat(trigger["sent_at"])
                diff_min = int((now - sent_at).total_seconds() / 60)
                trigger["response_time_min"] = diff_min
                PENDING_TRIGGERS_FILE.write_text("[]")
        except Exception:
            pass

    await log_emotion_data(text, analysis, trigger)

    # Discord転送
    await discord_ready.wait()
    channel = discord_client.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Discord channel {CHANNEL_ID} not found")
        return

    display = CONFIG['display_name']
    context_str = ""
    if trigger:
        context_str = (
            f"**きっかけ（YOU → {display}）:** "
            f"[{trigger.get('sent_at', '')[:16]} 送信 | "
            f"応答: {trigger.get('response_time_min', '?')}分]\n"
            f"> {trigger.get('message', '')}\n"
            f"> カテゴリ: {trigger.get('category', '')} "
            f"{' '.join(trigger.get('modifiers', []))}"
        )
    else:
        context_str = f"**きっかけ:** {display}自発メッセージ"

    embed = Embed(title=f"📩 {display} [{time_str}]", color=0xe91e63)
    embed.add_field(name="🇬🇧 原文", value=f"> {text}", inline=False)
    if CONFIG.get('emotion_analysis', True):
        embed.add_field(
            name="📊 感情分析",
            value=f"```\n{emotion_bars}\n{att_risk}\n```",
            inline=False
        )
    if analysis.get("note"):
        embed.add_field(name="📝 補足", value=analysis["note"], inline=False)
    embed.add_field(name="🔗 コンテキスト", value=context_str, inline=False)
    embed.add_field(name="🇯🇵 日本語訳", value=analysis["translation"], inline=False)

    await channel.send(embed=embed)
    logger.info(f"Forwarded to Discord: {text[:50]}...")


async def handle_line_media(event: dict):
    user_id = event["source"]["userId"]
    msg = event["message"]
    msg_type = msg["type"]
    message_id = msg["id"]

    if not line_user_id:
        _save_user_id(user_id)

    label = "画像" if msg_type == "image" else "動画"
    emoji = "🖼️" if msg_type == "image" else "🎬"
    logger.info(f"LINE {label}: message_id={message_id}")

    add_to_conversation_buffer("person", f"[{label}]")

    # 会話ログ保存
    log_media(CONFIG['display_name'], "IN", msg_type)

    try:
        content_bytes, content_type = await download_line_content(message_id)
    except Exception as e:
        logger.error(f"Failed to download LINE content: {e}")
        await discord_ready.wait()
        channel = discord_client.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"📩 {CONFIG['display_name']} [{label}] ダウンロードエラー: {e}")
        return

    ext_map = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
        "video/mp4": ".mp4",
    }
    ext = ext_map.get(content_type, ".jpg" if msg_type == "image" else ".mp4")
    filename = f"{CONFIG['name']}_{msg_type}_{message_id}{ext}"
    size_mb = len(content_bytes) / (1024 * 1024)

    await discord_ready.wait()
    channel = discord_client.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Discord channel {CHANNEL_ID} not found")
        return

    now = datetime.now(JST)
    now_remote = now.astimezone(PERSON_TZ)
    tz_label = CONFIG.get('timezone_label', 'TZ')
    time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {tz_label}"

    embed = Embed(title=f"📩 {CONFIG['display_name']} [{time_str}]", color=0xe91e63)

    if size_mb > 8:
        embed.add_field(
            name=f"{emoji} {label}",
            value=f"⚠️ ファイルサイズ超過 ({size_mb:.1f}MB > 8MB)\nDiscordにアップロードできません",
            inline=False
        )
        await channel.send(embed=embed)
    else:
        embed.add_field(name=f"{emoji} {label}", value=f"サイズ: {size_mb:.1f}MB", inline=False)
        file = discord.File(io.BytesIO(content_bytes), filename=filename)
        if msg_type == "image":
            embed.set_image(url=f"attachment://{filename}")
        await channel.send(embed=embed, file=file)

    logger.info(f"Forwarded {label} to Discord: {message_id} ({size_mb:.1f}MB)")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "person": CONFIG.get('display_name', 'unknown'),
        "discord": discord_client.is_ready(),
        "line_id": bool(line_user_id),
        "time": datetime.now(JST).isoformat()
    }


# ============================================================
# メインエントリーポイント
# ============================================================
async def main():
    config_server = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config_server)

    display = CONFIG.get('display_name', 'Unknown')
    logger.info(f"Starting LINE Bot for {display} on port {PORT}...")
    logger.info(f"Discord channel: {CHANNEL_ID}")
    logger.info(f"LINE ID: {'Set' if line_user_id else 'Waiting for first message'}")

    await asyncio.gather(
        discord_client.start(DISCORD_TOKEN),
        server.serve()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='LINE ↔ Discord 翻訳Bot（汎用テンプレート）')
    parser.add_argument('--config', required=True, help='設定ファイル（JSON）のパス')
    args = parser.parse_args()

    config = load_config(args.config)
    init_globals(config)

    asyncio.run(main())
