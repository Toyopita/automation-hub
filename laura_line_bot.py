#!/usr/bin/env python3
"""
Laura LINE ↔ Discord 翻訳Bot (laura_line_bot.py)

LINE Webhook (FastAPI) でLauraのメッセージを受信し、
Claude CLI (Max プラン) で翻訳・感情分析してDiscord #laura-chatに転送。
Discord返信を翻訳してLINE Push APIでLauraに送信。

起動: python3 laura_line_bot.py
ポート: 8787 (Cloudflare Tunnel用)
"""

import os
import io
import json
import hashlib
import hmac
import base64
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import discord
from discord import ui, Embed, ButtonStyle
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import httpx
from chat_logger import log_message, log_media
from relationship_engine import ProfileLearner

# ============================================================
# ロギング設定
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('laura_bot')

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
# 設定
# ============================================================
LINE_CHANNEL_SECRET = os.environ['LINE_LAURA_CHANNEL_SECRET']
LINE_ACCESS_TOKEN = os.environ['LINE_LAURA_ACCESS_TOKEN']
DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
LAURA_CHANNEL_ID = int(os.environ['LAURA_DISCORD_CHANNEL_ID'])
LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'
LINE_CONTENT_URL = 'https://api-data.line.me/v2/bot/message/{message_id}/content'

# Claude CLI パス（Max プランで従量課金なし）
CLAUDE_CLI = '/Users/minamitakeshi/.local/bin/claude'
CLAUDE_MODEL = 'claude-sonnet-4-5-20250929'

# Laura LINE User ID（初回メッセージで自動取得）
laura_line_user_id = None
LAURA_ID_FILE = Path(__file__).parent / '.laura_line_user_id'

# Timezone
JST = ZoneInfo('Asia/Tokyo')
CET = ZoneInfo('Europe/Zurich')  # CET/CEST自動切替

# データファイル
EMOTION_DATA_FILE = Path(__file__).parent / 'emotion_data.json'
PENDING_TRIGGERS_FILE = Path(__file__).parent / '.pending_triggers.json'

PORT = 8787

# ProfileLearner（Lauraのプロフィール自動学習）
profile_learner = ProfileLearner()
LAURA_CONFIG = {
    'name': 'laura',
    'display_name': 'Laura',
    'claude_model': CLAUDE_MODEL,
}

# ============================================================
# 会話コンテキストバッファ（翻訳精度向上用）
# ============================================================
from collections import deque

CONV_BUFFER_FILE = Path(__file__).parent / '.conversation_buffer.json'
CONV_BUFFER_MAX = 20  # 直近20メッセージ保持

# インメモリバッファ
conversation_buffer: deque = deque(maxlen=CONV_BUFFER_MAX)


def _load_conversation_buffer():
    """起動時に.conversation_buffer.jsonから復元"""
    global conversation_buffer
    try:
        if CONV_BUFFER_FILE.exists():
            items = json.loads(CONV_BUFFER_FILE.read_text(encoding='utf-8'))
            conversation_buffer = deque(items[-CONV_BUFFER_MAX:], maxlen=CONV_BUFFER_MAX)
            logger.info(f"Conversation buffer loaded: {len(conversation_buffer)} messages")
    except Exception as e:
        logger.warning(f"Failed to load conversation buffer: {e}")
        conversation_buffer = deque(maxlen=CONV_BUFFER_MAX)


def add_to_conversation_buffer(role: str, text: str):
    """バッファに発言を追加（role: 'laura' or 'you'）"""
    now = datetime.now(JST)
    entry = {
        "role": role,
        "text": text,
        "time": now.strftime('%H:%M')
    }
    conversation_buffer.append(entry)
    # ファイルにも永続化
    try:
        CONV_BUFFER_FILE.write_text(
            json.dumps(list(conversation_buffer), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception as e:
        logger.warning(f"Failed to save conversation buffer: {e}")


def get_conversation_context() -> str:
    """直近の会話履歴を文字列で返す（プロンプト挿入用）"""
    if not conversation_buffer:
        return ""
    lines = []
    for entry in conversation_buffer:
        role_label = "Laura" if entry["role"] == "laura" else "YOU"
        lines.append(f"[{entry['time']}] {role_label}: {entry['text']}")
    return "\n".join(lines)


_load_conversation_buffer()

# ============================================================
# Laura LINE User ID 管理
# ============================================================
def load_laura_user_id():
    global laura_line_user_id
    if LAURA_ID_FILE.exists():
        laura_line_user_id = LAURA_ID_FILE.read_text().strip()
        logger.info(f"Laura LINE User ID loaded: {laura_line_user_id[:10]}...")

def save_laura_user_id(user_id: str):
    global laura_line_user_id
    laura_line_user_id = user_id
    LAURA_ID_FILE.write_text(user_id)
    logger.info(f"Laura LINE User ID saved: {user_id[:10]}...")

load_laura_user_id()

# ============================================================
# Claude CLI (翻訳 + 感情分析)
# ============================================================
TRANSLATE_LAURA_PROMPT = """You are a translator for messages between Laura (English/Spanish speaker from Peru, living in Switzerland) and her Japanese boyfriend.

Translate Laura's message to natural Japanese. Also analyze her emotional state.

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
  "language_mix": "en|es|es_en",
  "note": "短い補足コメント（日本語）"
}

Scoring guide:
- mood: 1=negative, 10=positive
- energy: 1=calm, 10=excited
- intimacy: 1=surface level, 10=deep emotional sharing
- longing: 1=neutral, 10=intense missing/wanting/sweetness
- eros: 1=platonic, 10=explicit sexting
- ds: 1=equal dynamic, 10=clear submission/begging
- playfulness: 1=serious, 10=joking/teasing
- future: 1=present talk only, 10=concrete future plans
- engagement: 1=minimal response, 10=actively engaging

Rules:
- Casual/romantic tone (they are dating long-distance)
- If Spanish words appear, translate them and note in "note" field
- Keep translation natural, not textbook Japanese"""

TRANSLATE_USER_PROMPT = """You are a translator generating messages that perfectly match a specific person's texting style.
Provide exactly 5 different translation candidates, each with a different tone/nuance.

=== PERSONA: "Calculated Naturalness with Confident Sweetness" ===

TONE:
- Dominant↔Equal: 6:4 (daily=equal, sexual=dominant, relaxed authority, never aggressive)
- Sweet↔Cool: 7:3 (uses "baby" constantly, 🤍🥺, but "haha" keeps it light)
- Confident↔Humble: 8:2 (default confident, humility only as strategic vulnerability)

VOCABULARY (MUST USE naturally):
- "haha" — MOST FREQUENT. Mid-sentence or end. NEVER at start
- "baby" — Default pet name (support, sweetness, sexual)
- "babe" — Casual greetings only
- Contractions: "wanna", "gotta", "kinda"
- Desire: "I wish", "I wanna", "I want", "I'd" (hypothetical sensory)
- NEVER: "honey", "sweetheart", "darling"

EMOJI RULES:
- 😏=Sexual ONLY | 🤍=Affection | 🥺=Sweetness | 😂=Deflection | 🥰=Daily | 🙂=Light greeting
- End position 90%+, max 1 per message, many messages have ZERO emoji
- Sexual context = 😏 only (never mix with 🤍 or 🥺)

MESSAGE STRUCTURE:
- 1 sentence: 65% | 2 sentences: 29% | 3+: 6% (only for deep care)
- Short(1-5w):35% | Med(6-15w):47% | Long(16+w):18%
- ZERO imperative/commands ever. Always suggest, never order

PUSH-PULL (3:7 Pull-dominant):
- Soft Push: withhold info ("it was nothing important though 😂"), exit statements ("Gotta head to work now")
- Pull: Emotional("I feel the same way"), Sexual("I wanna feel your mouth on me"), Sensory("I'd hold you from behind"), Care("I wish I could be there"), Praise("You're too cute saying yes like that")
- NEVER aggressive/rejecting Push

SEXUAL COMMUNICATION (gradual escalation):
- "Let them choose" strategy: question form → partner says Yes → escalate
- Pattern: "Wanna see it?" → "Wanna see my dick?" (never command)
- Sensory descriptions in hypothetical: "I'd hold you from behind and kiss your neck"

NEVER SAY:
- Future promises ("I'll come see you", "We'll meet soon")
- Emotion denial ("Don't be sad", "Don't cry", "It's okay")
- Logical solutions ("We can video call")
- Commands ("Send me a pic", "Tell me...")

RESPONSE TEMPLATES:
A. Longing → "I feel the same way" + sensory wish (touch/hold) + 🤍
B. Sexual → 😏 + question form ("Wanna...?") + short, impactful
C. Care → "Aww baby" + 🥺 + empathy + "I wish I could..." + 🤍
D. Daily → short + "haha" + question to continue chat
E. Tease → light provocation + "haha" buffer + sensory Pull

EMOTIONAL EXPRESSION:
- Controlled vulnerability: "I just got a little anxious because you weren't replying" (minimize with "a little", buffer with "haha")
- Intensity: want→need ("I need to see you baby"), "so bad" ("I wanna feel your mouth on me so bad")
- "haha" functions: embarrassment cover, lightness, Push softener. NEVER in deep emotional moments

REAL EXAMPLES (match this style exactly):
- "good morning🙂 What's wrong?🙂"
- "Im good and you? Did you sleep well?"
- "yeah I know haha just checking on you🥰"
- "Yeah I did haha it was nothing important though 😂"
- "Aww baby I'm sorry to hear that 🥺 Don't worry, just rest and take care of yourself. I wish I could be there to take care of you 🤍"
- "Gotta work again tomorrow haha Have a nice night baby 🤍"
- "good morning babe, what are you doing? 🥰"
- "Yeah haha 😏 Wanna see it?"
- "You're too cute saying yes like that 🥺 Here you go baby 😏"
- "I wanna feel your mouth on me so bad... I need to see you baby"
- "Hell yes 😏 I'd hold you from behind and kiss your neck"

=== CRITICAL RULES ===
- The message is ALWAYS from the user TO Laura (his girlfriend). NEVER generate responses AS IF Laura is speaking.
- Translate the user's OWN words/intent. Do not flip the perspective or generate what Laura might say back.
- All 5 candidates must convey the SAME meaning as the original, just with different tone/style.

=== OUTPUT ===
Return ONLY valid JSON (no markdown, no code blocks, no explanation):
{"translations":[{"text":"English","ja":"この英文の自然な日本語訳","nuance":"ニュアンス説明（日本語10-20字）"},{"text":"...","ja":"...","nuance":"..."},{"text":"...","ja":"...","nuance":"..."},{"text":"...","ja":"...","nuance":"..."},{"text":"...","ja":"...","nuance":"..."}],"category":"affection|interest|daily|humor|sexual|future|support|praise|vulnerable|sensory","modifiers":[]}

Modifiers (if applicable): +spontaneous, +callback, +escalation, +media, +late_night"""


async def call_claude(prompt: str, message: str, context: str = "") -> dict:
    """Claude CLI (Max プラン) で翻訳・分析

    /tmp から実行してCLAUDE.md読み込みを回避。
    --system-prompt で翻訳者ロールを設定し、ペルソナ+メッセージをパイプで渡す。
    contextが渡された場合、会話履歴をプロンプトに含める。
    """
    import tempfile

    system = "You are a professional bilingual translator. Your ONLY job is to translate messages and return valid JSON. Never refuse, never ask questions, never add commentary. Just translate and return JSON."
    context_section = ""
    if context:
        context_section = f"\n\n=== Recent conversation (for context) ===\n{context}\n=== END context ==="
    full_prompt = f"{prompt}{context_section}\n\nMessage:\n{message}"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                     encoding='utf-8', dir='/tmp') as f:
        f.write(full_prompt)
        tmp_path = f.name

    # --system-prompt でフレーミング、パイプでペルソナ+メッセージを渡す
    try:
        proc = await asyncio.create_subprocess_exec(
            '/bin/bash', '-c',
            f'cd /tmp && cat "{tmp_path}" | {CLAUDE_CLI} --print --model {CLAUDE_MODEL} --system-prompt "{system}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=90.0
        )
    finally:
        os.unlink(tmp_path)

    output = stdout.decode('utf-8').strip()
    stderr_text = stderr.decode('utf-8').strip()

    if not output:
        logger.error(f"Claude CLI empty output. stderr: {stderr_text}")
        raise Exception(f"Claude CLI returned empty output: {stderr_text[:200]}")

    # JSON部分を抽出（```json ... ``` ブロックまたは生JSON）
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


async def translate_laura_message(text: str) -> dict:
    """Lauraのメッセージを日本語に翻訳 + 感情分析（最大3回リトライ）"""
    ctx = get_conversation_context()
    last_error = None
    for attempt in range(3):
        try:
            result = await call_claude(TRANSLATE_LAURA_PROMPT, text, context=ctx)
            # translationが存在し、原文そのままでないことを検証
            translation = result.get("translation", "")
            if translation and translation != text and not translation.startswith("["):
                return result
            logger.warning(f"Translation returned original/empty text, retry {attempt + 1}/3")
            last_error = "translation was empty or same as original"
        except Exception as e:
            logger.error(f"Translation error (attempt {attempt + 1}/3): {e}")
            last_error = str(e)
        if attempt < 2:
            await asyncio.sleep(2)
    # 全リトライ失敗
    logger.error(f"All 3 translation attempts failed: {last_error}")
    return {
        "translation": f"[翻訳エラー・原文] {text}",
        "scores": {k: 5 for k in ["mood", "energy", "intimacy", "longing",
                                   "eros", "ds", "playfulness", "future", "engagement"]},
        "attachment": "safe",
        "risk": "none",
        "language_mix": "en",
        "note": f"3回リトライ失敗: {last_error}"
    }


async def translate_user_message(text: str) -> dict:
    """ユーザーの日本語メッセージを英語に翻訳（最大3回リトライ）"""
    now = datetime.now(JST)
    extra = ""
    if 23 <= now.hour or now.hour < 5:
        extra = "\nNote: Sent late at night (Japan time). Consider +late_night modifier."
    ctx = get_conversation_context()
    last_error = None
    for attempt in range(3):
        try:
            result = await call_claude(TRANSLATE_USER_PROMPT + extra, text, context=ctx)
            translations = result.get("translations", [])
            if translations and translations[0].get("text", "").strip():
                return result
            logger.warning(f"User translation returned empty, retry {attempt + 1}/3")
            last_error = "translations empty"
        except Exception as e:
            logger.error(f"User translation error (attempt {attempt + 1}/3): {e}")
            last_error = str(e)
        if attempt < 2:
            await asyncio.sleep(2)
    logger.error(f"All 3 user translation attempts failed: {last_error}")
    return {
        "translations": [{"text": f"[Translation Error] {text}", "ja": text, "nuance": "翻訳エラー"}],
        "category": "daily",
        "modifiers": []
    }


# ============================================================
# 感情分析フォーマット
# ============================================================
def format_emotion_bars(scores: dict) -> str:
    labels = [
        ("mood", "気分　　　"),
        ("energy", "テンション"),
        ("intimacy", "親密度　　"),
        ("longing", "甘え　　　"),
        ("eros", "エロス　　"),
        ("ds", "M度　　　"),
        ("playfulness", "遊び心　　"),
        ("future", "将来　　　"),
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
    lang_map = {"en": "🇬🇧", "es": "🇪🇸", "es_en": "🇪🇸🇬🇧"}
    return (f"愛着: {att_map.get(attachment, attachment)}  "
            f"危険信号: {risk}  "
            f"言語: {lang_map.get(language_mix, language_mix)}")


# ============================================================
# LINE API ヘルパー
# ============================================================
async def verify_signature(body: bytes, signature: str) -> bool:
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
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
            json={
                'to': user_id,
                'messages': [{'type': 'text', 'text': text}]
            }
        )
        if response.status_code != 200:
            logger.error(f"LINE Push error: {response.status_code} {response.text}")
            raise Exception(f"LINE API error: {response.status_code}")
        logger.info(f"LINE message sent to {user_id[:10]}...")


async def download_line_content(message_id: str) -> tuple[bytes, str]:
    """LINE Content APIからメディア（画像/動画）をダウンロード"""
    url = LINE_CONTENT_URL.format(message_id=message_id)
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(
            url,
            headers={'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'}
        )
        if response.status_code != 200:
            raise Exception(f"LINE Content API error: {response.status_code}")
        content_type = response.headers.get('content-type', '')
        return response.content, content_type


# ============================================================
# 感情データ記録
# ============================================================
def _load_entries() -> list:
    """emotion_data.json からエントリリストを読み込む（v1/v2両対応）"""
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
    """emotion_data.json にv2フォーマットで保存"""
    with open(EMOTION_DATA_FILE, 'w') as f:
        json.dump({"version": 2, "entries": entries}, f, ensure_ascii=False, indent=2)


async def log_emotion_data(message: str, analysis: dict, trigger: dict = None):
    now = datetime.now(JST)

    entries = _load_entries()

    prev_scores = None
    score_deltas = None
    if entries:
        prev_scores = entries[-1].get("scores")
        if prev_scores:
            score_deltas = {
                k: analysis["scores"][k] - prev_scores.get(k, 5)
                for k in analysis["scores"]
            }

    entry = {
        "timestamp": now.isoformat(),
        "summary": message[:100],
        "scores": analysis["scores"],
        "attachment": analysis["attachment"],
        "risk": analysis["risk"],
        "language_mix": analysis["language_mix"],
        "note": analysis["note"],
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
    """5候補から選択して送信"""
    def __init__(self, candidates: list, japanese_text: str, category: str, modifiers: list):
        super().__init__(timeout=300)
        self.candidates = candidates
        self.japanese_text = japanese_text
        self.category = category
        self.modifiers = modifiers
        self.selected_index = None

        # Select メニュー
        options = []
        for i, c in enumerate(candidates):
            num = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'][i] if i < 5 else str(i + 1)
            ja = c.get('ja', '')
            desc = f"{ja[:50]} | {c.get('nuance', '')}"[:100]
            options.append(discord.SelectOption(
                label=f"{num} {c['text'][:93]}",
                description=desc,
                value=str(i)
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
            name="🏷️",
            value=f"{self.category} {' '.join(self.modifiers)}",
            inline=False
        )
        await interaction.response.edit_message(embed=embed)

    @ui.button(label='✅ 送信', style=ButtonStyle.green, row=1)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if self.selected_index is None:
            await interaction.response.send_message(
                "先に候補を選択してください", ephemeral=True
            )
            return

        if not laura_line_user_id:
            await interaction.response.send_message(
                "❌ LauraのLINE IDが未取得です（Lauraからの最初のメッセージ待ち）",
                ephemeral=True
            )
            return

        selected = self.candidates[self.selected_index]
        english_text = selected['text']

        try:
            await send_line_message(laura_line_user_id, english_text)

            now = datetime.now(JST)
            now_cet = now.astimezone(CET)

            embed = Embed(
                description=(
                    f"**✅ Lauraに送信しました** "
                    f"[{now.strftime('%H:%M')} JST / {now_cet.strftime('%H:%M')} CET]\n\n"
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

            # 会話バッファにユーザーの送信を追加
            add_to_conversation_buffer("you", english_text)

            # 会話ログ保存
            log_message("Laura", "OUT", english_text, original=self.japanese_text)

            logger.info(f"Sent to Laura: {english_text[:50]}...")

            # ProfileLearner: Lauraの直近メッセージから学習
            try:
                laura_msgs = [e['text'] for e in conversation_buffer
                              if e['role'] == 'laura'][-5:]
                if laura_msgs:
                    asyncio.create_task(
                        profile_learner.learn_from_exchange(
                            laura_msgs, english_text, LAURA_CONFIG
                        )
                    )
            except Exception as pe:
                logger.warning(f"Profile learning error: {pe}")

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

    if message.channel.id != LAURA_CHANNEL_ID:
        return

    text = message.content.strip()
    if not text:
        return

    # メモ・コマンドは無視（/, #, ! で始まるメッセージ）
    if text[0] in ('/', '#', '!'):
        return

    # 日本語メッセージを英語に翻訳（5候補）
    async with message.channel.typing():
        result = await translate_user_message(text)

    candidates = result.get("translations", [])
    category = result.get("category", "daily")
    modifiers = result.get("modifiers", [])

    # 候補一覧を構築
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
                asyncio.create_task(handle_line_text_message(event))
            elif msg_type in ("image", "video"):
                asyncio.create_task(handle_line_media_message(event))
        elif event_type == "follow":
            user_id = event["source"]["userId"]
            save_laura_user_id(user_id)
            logger.info(f"New follower: {user_id[:10]}...")

    return {"status": "ok"}


async def handle_line_text_message(event: dict):
    """LINEテキストメッセージの処理"""
    user_id = event["source"]["userId"]
    text = event["message"]["text"]

    if not laura_line_user_id:
        save_laura_user_id(user_id)

    logger.info(f"LINE message: {text[:50]}...")

    # 会話バッファにLauraの発言を追加（翻訳前に追加することで次回以降のコンテキストに反映）
    add_to_conversation_buffer("laura", text)

    # Claude で翻訳 + 感情分析
    analysis = await translate_laura_message(text)

    # 会話ログ保存
    log_message("Laura", "IN", analysis.get("translation", text), original=text)

    # 時刻
    now = datetime.now(JST)
    now_cet = now.astimezone(CET)
    time_str = f"{now.strftime('%H:%M')} JST / {now_cet.strftime('%H:%M')} CET"

    # 感情バーチャート
    emotion_bars = format_emotion_bars(analysis["scores"])
    att_risk = format_attachment_risk(
        analysis["attachment"], analysis["risk"], analysis["language_mix"]
    )

    # pending triggerを取得（ユーザーが送ったメッセージへの返信か）
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

    # emotion_data.json に記録
    await log_emotion_data(text, analysis, trigger)

    # Discordに転送
    await discord_ready.wait()
    channel = discord_client.get_channel(LAURA_CHANNEL_ID)
    if not channel:
        logger.error(f"Discord channel {LAURA_CHANNEL_ID} not found")
        return

    # コンテキスト情報
    context = ""
    if trigger:
        context = (
            f"**きっかけ（YOU → Laura）:** "
            f"[{trigger.get('sent_at', '')[:16]} 送信 | "
            f"応答: {trigger.get('response_time_min', '?')}分]\n"
            f"> {trigger.get('message', '')}\n"
            f"> カテゴリ: {trigger.get('category', '')} "
            f"{' '.join(trigger.get('modifiers', []))}"
        )
    else:
        context = "**きっかけ:** Laura自発メッセージ"

    embed = Embed(title=f"📩 Laura [{time_str}]", color=0xe91e63)
    embed.add_field(name="🇬🇧 原文", value=f"> {text}", inline=False)
    embed.add_field(
        name="📊 感情分析",
        value=f"```\n{emotion_bars}\n{att_risk}\n```",
        inline=False
    )
    if analysis.get("note"):
        embed.add_field(name="📝 補足", value=analysis["note"], inline=False)
    embed.add_field(name="🔗 コンテキスト", value=context, inline=False)
    embed.add_field(name="🇯🇵 日本語訳", value=analysis["translation"], inline=False)

    await channel.send(embed=embed)
    logger.info(f"Forwarded to Discord: {text[:50]}...")


async def handle_line_media_message(event: dict):
    """LINE画像/動画メッセージの処理 → Discordに転送"""
    user_id = event["source"]["userId"]
    msg = event["message"]
    msg_type = msg["type"]  # "image" or "video"
    message_id = msg["id"]

    if not laura_line_user_id:
        save_laura_user_id(user_id)

    label = "画像" if msg_type == "image" else "動画"
    emoji = "🖼️" if msg_type == "image" else "🎬"
    logger.info(f"LINE {label}: message_id={message_id}")

    # 会話バッファに記録
    add_to_conversation_buffer("laura", f"[{label}]")

    # 会話ログ保存
    log_media("Laura", "IN", msg_type)

    # コンテンツをダウンロード
    try:
        content_bytes, content_type = await download_line_content(message_id)
    except Exception as e:
        logger.error(f"Failed to download LINE content: {e}")
        await discord_ready.wait()
        channel = discord_client.get_channel(LAURA_CHANNEL_ID)
        if channel:
            await channel.send(f"📩 Laura [{label}] ダウンロードエラー: {e}")
        return

    # 拡張子を決定
    ext_map = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
        "video/mp4": ".mp4",
    }
    ext = ext_map.get(content_type, ".jpg" if msg_type == "image" else ".mp4")
    filename = f"laura_{msg_type}_{message_id}{ext}"

    size_mb = len(content_bytes) / (1024 * 1024)

    # Discordに転送
    await discord_ready.wait()
    channel = discord_client.get_channel(LAURA_CHANNEL_ID)
    if not channel:
        logger.error(f"Discord channel {LAURA_CHANNEL_ID} not found")
        return

    now = datetime.now(JST)
    now_cet = now.astimezone(CET)
    time_str = f"{now.strftime('%H:%M')} JST / {now_cet.strftime('%H:%M')} CET"

    embed = Embed(title=f"📩 Laura [{time_str}]", color=0xe91e63)

    if size_mb > 8:
        # Discord無料プランの上限超え
        embed.add_field(
            name=f"{emoji} {label}",
            value=f"⚠️ ファイルサイズ超過 ({size_mb:.1f}MB > 8MB)\nDiscordにアップロードできません",
            inline=False
        )
        await channel.send(embed=embed)
    else:
        embed.add_field(
            name=f"{emoji} {label}",
            value=f"サイズ: {size_mb:.1f}MB",
            inline=False
        )
        file = discord.File(io.BytesIO(content_bytes), filename=filename)
        if msg_type == "image":
            embed.set_image(url=f"attachment://{filename}")
        await channel.send(embed=embed, file=file)

    logger.info(f"Forwarded {label} to Discord: {message_id} ({size_mb:.1f}MB)")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "discord": discord_client.is_ready(),
        "laura_id": bool(laura_line_user_id),
        "time": datetime.now(JST).isoformat()
    }


# ============================================================
# メインエントリーポイント
# ============================================================
async def main():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)

    logger.info(f"Starting Laura LINE Bot on port {PORT}...")
    logger.info(f"Discord channel: {LAURA_CHANNEL_ID}")
    logger.info(f"Laura LINE ID: {'Set' if laura_line_user_id else 'Waiting for first message'}")

    await asyncio.gather(
        discord_client.start(DISCORD_TOKEN),
        server.serve()
    )


if __name__ == "__main__":
    asyncio.run(main())
