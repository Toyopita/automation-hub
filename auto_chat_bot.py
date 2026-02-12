#!/usr/bin/env python3
"""
汎用 自律型LINE Chat Bot（Relationship Engine統合）

configファイルで対象人物をカスタマイズ可能。
aljela_auto_bot.py をテンプレート化した汎用版。

機能:
- 自動応答（Claude CLIでユーザーペルソナ生成）
- 月200通制限の自動管理（日割り＋曜日＋モメンタム）
- 返信タイミング制御（ランダム遅延、深夜無応答）
- メッセージバッチング（連続メッセージをまとめて処理）
- Discord監視ログ＋手動介入
- 関係性ステージ追跡
- プロアクティブ会話開始

使い方:
  python3 auto_chat_bot.py --config aljela_config.json
  python3 auto_chat_bot.py --config newperson_config.json
"""

import os
import io
import json
import hashlib
import hmac
import base64
import asyncio
import argparse
import calendar
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from collections import deque

import discord
from discord import ui, Embed, ButtonStyle
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import httpx

from relationship_engine import (
    ProfileLearner, StrategyEngine, StageManager,
    PersonaAdapter, TimingController, ProactiveScheduler,
    BotDetectionFilter, _call_claude_json,
)
from episode_memory import compress_to_episode, format_episodes_for_prompt
from profile_consolidator import should_consolidate, consolidate_profile, increment_exchange_count
from chat_logger import log_message, log_media, log_system

# ============================================================
# ロギング
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ============================================================
# 環境変数
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
# 定数
# ============================================================
BASE_DIR = Path(__file__).parent
JST = ZoneInfo('Asia/Tokyo')
LINE_PUSH_URL = 'https://api.line.me/v2/bot/message/push'
LINE_CONTENT_URL = 'https://api-data.line.me/v2/bot/message/{message_id}/content'
CLAUDE_CLI = '/Users/minamitakeshi/.local/bin/claude'
MONTHLY_LIMIT = 200
RESERVE = 15  # 月末用リザーブ


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
# AutoChatBot クラス
# ============================================================
class AutoChatBot:
    """config駆動の自律型チャットBot"""

    def __init__(self, config: dict):
        self.config = config
        self.name = config['name'].lower()
        self.display_name = config.get('display_name', self.name.capitalize())
        self.person_tz = ZoneInfo(config.get('timezone', 'Asia/Manila'))
        self.tz_label = config.get('timezone_label', 'TZ')
        self.port = config.get('port', 8788)
        self.claude_model = config.get('claude_model', 'claude-sonnet-4-5-20250929')

        # 環境変数
        env = config['env']
        self.line_channel_secret = os.environ.get(env['line_channel_secret'], '')
        self.line_access_token = os.environ.get(env['line_access_token'], '')
        self.discord_token = os.environ.get(env['discord_token'], '')
        self.channel_id = int(os.environ.get(env['discord_channel_id'], '0'))

        # ロガー
        self.logger = logging.getLogger(f'{self.name}_bot')

        # データファイル（全て {name}_xxx パターン）
        self.user_id_file = BASE_DIR / f'.{self.name}_line_user_id'
        self.conv_buffer_file = BASE_DIR / f'.{self.name}_conversation_buffer.json'
        self.budget_file = BASE_DIR / f'{self.name}_budget.json'
        self.emotion_file = BASE_DIR / f'{self.name}_emotion_data.json'
        self.tunnel_log = BASE_DIR / f'{self.name}_tunnel.log'

        # Relationship Engine コンポーネント
        self.profile_learner = ProfileLearner()
        self.strategy_engine = StrategyEngine()
        self.stage_manager = StageManager()
        self.persona_adapter = PersonaAdapter()
        self.timing_controller = TimingController()
        self.proactive_scheduler = ProactiveScheduler()

        # 状態
        self.line_user_id = None
        self.auto_respond_enabled = True
        self.conversation_buffer: deque = deque(maxlen=30)
        self.pending_messages: list = []
        self.batch_timer_task = None

        # 予算管理
        self.budget = MessageBudget(self.budget_file)

        # Discord
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = False
        self.discord_client = discord.Client(intents=intents)
        self.discord_ready = asyncio.Event()

        # FastAPI
        self.app = FastAPI()

        # 初期化
        self._load_user_id()
        self._load_conversation_buffer()
        self._setup_discord_events()
        self._setup_routes()

    # ============================================================
    # LINE User ID
    # ============================================================
    def _load_user_id(self):
        if self.user_id_file.exists():
            self.line_user_id = self.user_id_file.read_text().strip()
            self.logger.info(f"LINE User ID loaded: {self.line_user_id[:10]}...")

    def _save_user_id(self, uid: str):
        self.line_user_id = uid
        self.user_id_file.write_text(uid)
        self.logger.info(f"LINE User ID saved: {uid[:10]}...")

    # ============================================================
    # 会話バッファ
    # ============================================================
    def _load_conversation_buffer(self):
        try:
            if self.conv_buffer_file.exists():
                items = json.loads(self.conv_buffer_file.read_text(encoding='utf-8'))
                self.conversation_buffer = deque(items[-30:], maxlen=30)
                self.logger.info(f"Conversation buffer loaded: {len(self.conversation_buffer)} messages")
        except Exception as e:
            self.logger.warning(f"Buffer load failed: {e}")

    def _save_conversation_buffer(self):
        try:
            self.conv_buffer_file.write_text(
                json.dumps(list(self.conversation_buffer), ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            self.logger.warning(f"Buffer save failed: {e}")

    def add_message(self, role: str, text: str):
        """role: person名 or 'you'"""
        now = datetime.now(JST)

        # Check if buffer is about to overflow — compress oldest messages to episode
        if len(self.conversation_buffer) >= self.conversation_buffer.maxlen - 1:
            oldest_5 = list(self.conversation_buffer)[:5]
            if oldest_5:
                asyncio.create_task(self._compress_oldest_to_episode(oldest_5))

        self.conversation_buffer.append({
            "role": role,
            "text": text,
            "time": now.strftime('%Y-%m-%d %H:%M')
        })
        self._save_conversation_buffer()

    async def _compress_oldest_to_episode(self, messages: list[dict]):
        """Compress old messages into an episode before they're lost from the buffer."""
        try:
            episode = await compress_to_episode(
                messages=messages,
                name=self.name,
                display_name=self.display_name,
                model=self.claude_model,
            )
            if episode:
                self.logger.info(f"Episode {episode.get('id')} created: {episode.get('summary', '')[:60]}...")
        except Exception as e:
            self.logger.error(f"Episode compression failed (non-fatal): {e}")

    def get_conversation_history(self) -> str:
        if not self.conversation_buffer:
            return "(No previous conversation)"
        lines = []
        for e in self.conversation_buffer:
            label = self.display_name if e["role"] == self.name else "YOU"
            lines.append(f"[{e['time']}] {label}: {e['text']}")
        return "\n".join(lines)

    # ============================================================
    # 感情分析
    # ============================================================
    async def translate_to_japanese(self, messages: list[str]) -> str:
        """受信メッセージを日本語に翻訳"""
        combined = "\n".join(messages)
        # 相手の背景情報を取得
        bg = self.config.get("background", "")
        lang_note = ""
        if "philipp" in bg.lower() or "manila" in bg.lower():
            lang_note = "送信者はフィリピン人で、英語は第二言語。文法が不完全な場合があるが、意図を汲み取って翻訳すること。"
        elif "indonesia" in bg.lower() or "bandung" in bg.lower():
            lang_note = "送信者はインドネシア人で、英語は第二言語。直訳調の英語や独特の表現がある場合、意図を汲み取って自然な日本語にすること。"

        prompt = f"""以下のLINEチャットメッセージを日本語に翻訳してください。

{lang_note}

【翻訳の目的】
この翻訳は30代日本人男性が、相手のメッセージ内容を確認するために読むもの。
「相手がどう言ったか」の意味を正確に、自然な日本語で伝えること。

【トーンルール（厳守）】
- 一人称: 使う場合は「自分」または省略。「俺」は禁止。
- 二人称: 「君」または相手の名前。「お前」は絶対禁止。
- 目指すトーン: 30代知的男性のナチュラルな口語（落ち着き＋カジュアル）
- イメージ: 友人と落ち着いたバーで話すときの口調

【禁止表現】
- 「お前」「てか」「マジで」「ガチで」「あんま」→ 粗暴/若すぎ
- 代替: 「本当に」「正直」「あまり」「ところで」を使う

【翻訳ルール】
- 直訳NG。「何が言いたいか」を理解してから自然な日本語に
- 英語の構文をそのままなぞらない
- 「haha」「lol」→「笑」
- 絵文字はそのまま残す
- 打ち間違いや文法エラーは意図を推測して補完
- 複数メッセージは改行で区切る
- 翻訳のみ出力（説明・引用符・接頭辞は不要）

メッセージ:
{combined}"""
        system = "あなたはプロのローカライズ翻訳者です。ESL話者のカジュアルなチャットを、30代日本人男性が一読で意味を掴める自然な口語体に翻訳します。「俺」「お前」「てか」「マジ」等の粗暴・若者言葉は禁止。落ち着いたカジュアルな口調で。翻訳のみ出力。"
        try:
            from relationship_engine import _call_claude_cli
            result = await _call_claude_cli(prompt, system, model=self.claude_model)
            return result.strip()
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return ""

    async def analyze_emotion(self, messages: list[str]) -> dict:
        prompt = EMOTION_ANALYSIS_PROMPT.format(messages="\n".join(f"- {m}" for m in messages))
        system = "You are an emotional intelligence analyst. Return ONLY valid JSON. No explanation."
        return await _call_claude_json(prompt, system, model=self.claude_model)

    def _load_emotion_entries(self) -> list:
        if not self.emotion_file.exists():
            return []
        try:
            with open(self.emotion_file) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("entries", [])
            return []
        except Exception:
            return []

    def _save_emotion_entries(self, entries: list):
        with open(self.emotion_file, 'w') as f:
            json.dump({"version": 2, "entries": entries}, f, ensure_ascii=False, indent=2)

    def log_emotion_data(self, messages: list[str], analysis: dict) -> dict:
        now = datetime.now(JST)
        entries = self._load_emotion_entries()

        scores = analysis.get("scores", {})
        prev_scores = None
        score_deltas = None
        if entries:
            prev_scores = entries[-1].get("scores")
            if prev_scores:
                score_deltas = {
                    k: scores.get(k, 5) - prev_scores.get(k, 5)
                    for k in scores
                }

        entry = {
            "timestamp": now.isoformat(),
            "summary": " | ".join(m[:50] for m in messages[:3]),
            "scores": scores,
            "attachment": analysis.get("attachment", "safe"),
            "risk": analysis.get("risk", "none"),
            "note": analysis.get("note", ""),
            "prev_scores": prev_scores,
            "score_deltas": score_deltas,
        }

        entries.append(entry)
        self._save_emotion_entries(entries)
        self.logger.info("Emotion data logged")
        return entry

    # ============================================================
    # 返信生成
    # ============================================================
    async def generate_response(self, messages: list[str], emotion_analysis: dict = None,
                                strategy_decision=None,
                                detection_result: dict = None) -> dict:
        from relationship_engine import StrategyDecision

        profile = self.profile_learner.load_profile(self.name, self.display_name)
        rel = self.stage_manager.load_relationship(self.name, self.display_name)
        stage = rel.get('stage', 'friends')

        emotion = emotion_analysis or {'scores': {}, 'risk': 'none', 'attachment': 'safe'}

        if strategy_decision is None:
            strategy_decision = StrategyDecision()

        budget_info = {
            'daily_remaining': self.budget.get_daily_remaining(),
            'monthly_remaining': self.budget.get_monthly_remaining(),
        }

        prompt = self.persona_adapter.build_prompt(
            config=self.config,
            profile=profile,
            stage=stage,
            strategy=strategy_decision,
            emotion=emotion,
            budget=budget_info,
            conversation_history=list(self.conversation_buffer),
            messages=messages,
            detection_result=detection_result,
        )

        system = ("You are Toyo — a real person having a genuine LINE conversation. "
                  "Stay completely in character. Respond with authentic human emotion, "
                  "personal references, and natural imperfection. "
                  "Return ONLY valid JSON.")

        try:
            result = await _call_claude_json(prompt, system, model=self.claude_model)
            if "should_respond" in result:
                return result
            self.logger.warning("Invalid response format from Claude")
            return {"should_respond": False, "message": "", "reasoning": "Invalid response format"}
        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return {"should_respond": False, "message": "", "reasoning": f"Error: {e}"}

    # ============================================================
    # LINE API
    # ============================================================
    async def verify_signature(self, body: bytes, signature: str) -> bool:
        hash_val = hmac.new(self.line_channel_secret.encode(), body, hashlib.sha256).digest()
        expected = base64.b64encode(hash_val).decode()
        return hmac.compare_digest(expected, signature)

    async def send_line_message(self, text: str):
        if not self.line_user_id:
            self.logger.error("No LINE user ID")
            return False
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                LINE_PUSH_URL,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.line_access_token}'
                },
                json={'to': self.line_user_id, 'messages': [{'type': 'text', 'text': text}]}
            )
            if resp.status_code != 200:
                self.logger.error(f"LINE Push error: {resp.status_code} {resp.text}")
                return False
        self.logger.info(f"LINE sent: {text[:50]}...")
        return True

    async def download_line_content(self, message_id: str) -> tuple[bytes, str]:
        url = LINE_CONTENT_URL.format(message_id=message_id)
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            resp = await client.get(url, headers={'Authorization': f'Bearer {self.line_access_token}'})
            if resp.status_code != 200:
                raise Exception(f"Content API error: {resp.status_code}")
            return resp.content, resp.headers.get('content-type', '')

    # ============================================================
    # Discord
    # ============================================================
    def _setup_discord_events(self):
        bot = self

        @self.discord_client.event
        async def on_ready():
            bot.logger.info(f"Discord ready: {bot.discord_client.user}")
            bot.discord_ready.set()

        @self.discord_client.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            if message.channel.id != bot.channel_id:
                return
            if bot.auto_respond_enabled:
                return

            text = message.content.strip()
            if not text or text[0] in ('/', '#', '!'):
                return

            if not bot.budget.can_send():
                await message.reply("--- 今日/今月の送信上限に達しています")
                return

            success = await bot.send_line_message(text)
            if success:
                bot.budget.record_sent()
                bot.add_message("you", text)
                log_message(bot.display_name, "OUT", text,
                            metadata={"source": "手動介入"})
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")

    async def log_to_discord(self, title: str, description: str, color: int = 0x3498db, fields: list = None):
        await self.discord_ready.wait()
        channel = self.discord_client.get_channel(self.channel_id)
        if not channel:
            self.logger.error(f"Discord channel {self.channel_id} not found")
            return

        embed = Embed(title=title, description=description, color=color)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

        view = AutoRespondToggleView(self)
        await channel.send(embed=embed, view=view)

    async def notify_incoming_raw(self, text: str):
        """Immediately forward raw incoming message to Discord (before batch processing)."""
        try:
            await self.discord_ready.wait()
            channel = self.discord_client.get_channel(self.channel_id)
            if not channel:
                self.logger.error(f"Discord channel {self.channel_id} not found for raw notify")
                return
            now = datetime.now(JST)
            now_remote = now.astimezone(self.person_tz)
            time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {self.tz_label}"
            embed = Embed(
                title=f"💬 {self.display_name} ［{time_str}］",
                description=f"> {text}",
                color=0x9b59b6,
            )
            await channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Raw notify failed: {e}")

    async def log_incoming(self, messages: list[str], emotion_data: dict = None,
                           strategy_decision=None, translation: str = None):
        now = datetime.now(JST)
        now_remote = now.astimezone(self.person_tz)
        time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {self.tz_label}"

        msg_text = "\n".join(f"> {m}" for m in messages)
        remaining = self.budget.get_monthly_remaining()
        daily_rem = self.budget.get_daily_remaining()

        rel = self.stage_manager.load_relationship(self.name, self.display_name)
        current_stage = rel.get("stage", "friends")

        fields = [
            ("予算", f"今日: {daily_rem} / 月: {remaining}/{MONTHLY_LIMIT}", True),
            ("ステージ", current_stage, True),
            ("自動応答", "ON" if self.auto_respond_enabled else "OFF", True),
        ]

        if strategy_decision:
            strategy_text = (
                f"応答: {'する' if strategy_decision.should_respond else 'しない'}\n"
                f"エスカレーション: {strategy_decision.escalation_level:.1f}\n"
                f"トーン: {strategy_decision.tone_directive[:60]}"
            )
            if strategy_decision.topic_suggestion:
                strategy_text += f"\n話題: {strategy_decision.topic_suggestion}"
            if strategy_decision.end_conversation:
                strategy_text += "\n会話終了推奨"
            fields.append(("戦略", strategy_text, False))

        if emotion_data and emotion_data.get("scores"):
            scores = emotion_data["scores"]
            emotion_bars = format_emotion_bars(scores)
            att_risk = format_attachment_risk(
                emotion_data.get("attachment", "safe"),
                emotion_data.get("risk", "none")
            )
            fields.append(("📊 感情分析", f"```\n{emotion_bars}\n{att_risk}\n```", False))
            if emotion_data.get("note"):
                fields.append(("📝 補足", emotion_data["note"], False))
            risk = emotion_data.get("risk", "none")
            if risk in ("caution", "danger"):
                warning = "⚠️ 注意: " if risk == "caution" else "🚨 危険: "
                warning += "感情的に繊細な状態です"
                fields.append(("🔔 リスク警告", warning, False))
            score_deltas = emotion_data.get("score_deltas")
            if score_deltas:
                delta_parts = []
                for k, d in score_deltas.items():
                    if d != 0:
                        arrow = "↑" if d > 0 else "↓"
                        label = DELTA_LABELS_JA.get(k, k)
                        delta_parts.append(f"{label}{arrow}{abs(d)}")
                if delta_parts:
                    fields.append(("📈 変動", " ".join(delta_parts), False))

        if translation:
            fields.append(("🇯🇵 日本語訳", translation, False))

        await self.log_to_discord(
            f"📩 {self.display_name} ［{time_str}］",
            msg_text,
            color=0xcc5de8,
            fields=fields
        )

    async def log_outgoing(self, message: str, reasoning: str, delay_min: int,
                           topic_tags: list = None, push_pull_action: str = "neutral",
                           translation: str = ""):
        now = datetime.now(JST)
        now_remote = now.astimezone(self.person_tz)
        time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {self.tz_label}"
        remaining = self.budget.get_monthly_remaining()

        desc = f"> {message}"
        if translation:
            desc += f"\n\n🇯🇵 {translation}"

        fields = [
            ("遅延", f"{delay_min}分", True),
            ("月残", f"{remaining}/{MONTHLY_LIMIT}", True),
            ("Push/Pull", push_pull_action, True),
        ]

        if topic_tags:
            fields.append(("話題", ", ".join(topic_tags[:5]), True))

        fields.append(("判断理由", reasoning[:200], False))

        await self.log_to_discord(
            f"✅ You → {self.display_name} [{time_str}]",
            desc,
            color=0x2ecc71,
            fields=fields
        )

    async def log_skip(self, reasoning: str):
        now = datetime.now(JST)
        now_remote = now.astimezone(self.person_tz)
        time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {self.tz_label}"

        await self.log_to_discord(
            f"⏭️ スキップ [{time_str}]",
            "応答しない判断",
            color=0x95a5a6,
            fields=[("理由", reasoning[:300], False)]
        )

    # ============================================================
    # メッセージバッチング & 自動応答
    # ============================================================
    async def process_queued_messages(self):
        if not self.pending_messages:
            return

        messages = self.pending_messages.copy()
        self.pending_messages.clear()

        # 0. Bot検出判定
        detection_result = BotDetectionFilter.analyze_batch(messages)
        if detection_result["is_detection_query"]:
            count = BotDetectionFilter.track_detection(self.name)
            detection_result["prompt_addon"] = BotDetectionFilter.build_prompt_addon(
                detection_result["severity"], escalation_count=count
            )
            self.logger.warning(f"BOT DETECTION: severity={detection_result['severity']}, "
                                f"escalation={count}")
            # Discordにアラート
            await self.log_to_discord(
                f"ALERT: Identity Questioned ({detection_result['severity']})",
                f"Escalation count: {count}\nMessages: {' | '.join(messages[:3])}",
                color=0xff0000,
            )

        # 1. 感情分析
        emotion_result = None
        emotion_entry = None
        try:
            emotion_result = await self.analyze_emotion(messages)
            emotion_entry = self.log_emotion_data(messages, emotion_result)
            self.logger.info(f"Emotion analysis: {emotion_result.get('scores', {})}")
        except Exception as e:
            self.logger.warning(f"Emotion analysis failed (non-fatal): {e}")

        emotion = emotion_result or {'scores': {}, 'risk': 'none', 'attachment': 'safe'}

        # 2. プロファイルとリレーションシップ
        profile = self.profile_learner.load_profile(self.name, self.display_name)
        rel = self.stage_manager.load_relationship(self.name, self.display_name)
        stage = rel.get('stage', 'friends')

        # 3. 戦略判断
        strategy_decision = None
        try:
            budget_info = {
                'daily_remaining': self.budget.get_daily_remaining(),
                'monthly_remaining': self.budget.get_monthly_remaining(),
                'can_send': self.budget.can_send(),
            }
            reply_decision = emotion.get('reply_decision', {})
            strategy_decision = self.strategy_engine.decide(
                stage=stage,
                profile=profile,
                emotion=emotion,
                budget=budget_info,
                conversation_history=list(self.conversation_buffer),
                reply_decision=reply_decision,
            )
            rd_log = f", silence_risk={reply_decision.get('silence_risk', 'N/A')}" if reply_decision else ""
            self.logger.info(f"Strategy: respond={strategy_decision.should_respond}, "
                        f"tone={strategy_decision.tone_directive[:50]}, "
                        f"escalation={strategy_decision.escalation_level:.1f}"
                        f"{rd_log}")
        except Exception as e:
            self.logger.error(f"Strategy decision failed (non-fatal): {e}")
            from relationship_engine import StrategyDecision
            strategy_decision = StrategyDecision()

        # 4. 日本語翻訳
        translation = ""
        try:
            translation = await self.translate_to_japanese(messages)
        except Exception as e:
            self.logger.warning(f"Translation failed (non-fatal): {e}")

        # 5. Discordログ
        await self.log_incoming(messages, emotion_data=emotion_entry,
                           strategy_decision=strategy_decision,
                           translation=translation)

        # 5. 自動応答OFFチェック
        if not self.auto_respond_enabled:
            self.logger.info("Auto-respond disabled, skipping")
            return

        if self._is_sleep_time():
            self.logger.info("Sleep time, will respond later")
            now = datetime.now(JST)
            wake_time = now.replace(hour=7, minute=random.randint(5, 30), second=0)
            if wake_time <= now:
                wake_time += timedelta(days=1)
            delay = (wake_time - now).total_seconds()
            asyncio.create_task(self.delayed_respond(messages, int(delay),
                                                emotion_analysis=emotion_result,
                                                strategy_decision=strategy_decision,
                                                detection_result=detection_result))
            return

        # 6. 戦略的沈黙
        if not strategy_decision.should_respond:
            self.logger.info(f"Strategic silence: {strategy_decision.tone_directive}")
            await self.log_skip(f"Strategic silence: {strategy_decision.tone_directive}")
            return

        # 7. 予算チェック
        if not self.budget.can_send():
            self.logger.info("Budget exhausted, skipping")
            await self.log_skip("Budget exhausted for today/month")
            return

        # 8. 遅延計算
        delay = self.timing_controller.calculate_delay(
            stage=stage,
            profile=profile,
            emotion=emotion,
            conversation_buffer=list(self.conversation_buffer),
        )
        if strategy_decision.delay_override is not None:
            delay = strategy_decision.delay_override

        if delay < 0:
            self.logger.info("Delay=-1 (sleep), scheduling for morning")
            return

        self.logger.info(f"Will respond in {delay//60}min to {len(messages)} message(s)")
        asyncio.create_task(self.delayed_respond(messages, delay,
                                            emotion_analysis=emotion_result,
                                            strategy_decision=strategy_decision,
                                            detection_result=detection_result))

    async def delayed_respond(self, messages: list[str], delay_seconds: int,
                              emotion_analysis: dict = None,
                              strategy_decision=None,
                              detection_result: dict = None):
        delay_min = delay_seconds // 60
        self.logger.info(f"Waiting {delay_min}min before responding...")
        await asyncio.sleep(delay_seconds)

        if not self.auto_respond_enabled:
            self.logger.info("Auto-respond was disabled during wait")
            return

        if not self.budget.can_send():
            self.logger.info("Budget exhausted during wait")
            await self.log_skip("Budget exhausted during wait")
            return

        emotion = emotion_analysis or {'scores': {}, 'risk': 'none', 'attachment': 'safe'}

        try:
            result = await self.generate_response(messages, emotion_analysis=emotion_analysis,
                                             strategy_decision=strategy_decision,
                                             detection_result=detection_result)
        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            await self.log_skip(f"Generation error: {e}")
            return

        if not result.get("should_respond", False):
            reasoning = result.get("reasoning", "unknown")
            self.logger.info(f"Claude decided not to respond: {reasoning}")
            await self.log_skip(reasoning)
            return

        response_text = result.get("message", "")
        reasoning = result.get("reasoning", "")

        if not response_text.strip():
            self.logger.warning("Empty response from Claude")
            await self.log_skip("Generated response was empty")
            return

        success = await self.send_line_message(response_text)
        if success:
            self.budget.record_sent()
            self.add_message("you", response_text)
            log_message(self.display_name, "OUT", response_text,
                        metadata={"reasoning": reasoning[:100]})

            topic_tags = result.get("topic_tags", [])
            push_pull_action = result.get("push_pull_action", "neutral")

            # 送信メッセージの和訳
            out_translation = ""
            try:
                out_translation = await self.translate_to_japanese([response_text])
            except Exception:
                pass

            await self.log_outgoing(response_text, reasoning, delay_min,
                               topic_tags=topic_tags,
                               push_pull_action=push_pull_action,
                               translation=out_translation)
            self.logger.info(f"Auto-responded: {response_text[:50]}...")

            asyncio.create_task(self._post_response_processing(
                messages, response_text, result, emotion))
        else:
            await self.log_skip("LINE send failed")

    async def _post_response_processing(self, messages_in: list[str], message_out: str,
                                         response_json: dict, emotion: dict):
        try:
            learn_result = await self.profile_learner.learn_from_exchange(
                messages_in=messages_in,
                message_out=message_out,
                config=self.config,
            )
            self.logger.info(f"Profile learning: {len(learn_result.get('new_facts', []))} new facts")

            profile = self.profile_learner.load_profile(self.name, self.display_name)
            signals = self.stage_manager.evaluate_signals(response_json, profile, emotion)
            if signals:
                self.stage_manager.record_signals(self.name, signals, self.config)
                self.logger.info(f"Signals recorded: {len(signals)} "
                            f"(pos={sum(1 for s in signals if s.signal_type == 'positive')}, "
                            f"neg={sum(1 for s in signals if s.signal_type == 'negative')})")

            emotion_entries = self._load_emotion_entries()
            current_stage, new_stage = self.stage_manager.check_transition(
                self.name, self.config, emotion_history=emotion_entries)

            if new_stage and new_stage != current_stage:
                self.stage_manager.apply_transition(self.name, new_stage, self.config)
                self.logger.info(f"Stage transition: {current_stage} -> {new_stage}")
                log_system(self.display_name, "ステージ変更",
                           f"{current_stage} → {new_stage}")
                await self._log_stage_transition(current_stage, new_stage)

            self.stage_manager.update_daily_counters(self.name, self.config, emotion)

            # --- Profile consolidation trigger (every 20 exchanges) ---
            try:
                count = increment_exchange_count(self.name)
                if count >= 20 and should_consolidate(self.name):
                    self.logger.info(f"Triggering profile consolidation (exchange count: {count})")
                    asyncio.create_task(self._run_consolidation())
            except Exception as e:
                self.logger.warning(f"Consolidation check failed (non-fatal): {e}")

        except Exception as e:
            self.logger.error(f"Post-response processing error (non-fatal): {e}")

    async def _run_consolidation(self):
        """Run profile consolidation asynchronously."""
        try:
            stats = await consolidate_profile(self.name, model=self.claude_model)
            self.logger.info(f"Profile consolidation complete: {stats}")
        except Exception as e:
            self.logger.error(f"Profile consolidation failed (non-fatal): {e}")

    async def _log_stage_transition(self, old_stage: str, new_stage: str):
        now = datetime.now(JST)
        is_promotion = StageManager.STAGES.index(new_stage) > StageManager.STAGES.index(old_stage)
        color = 0xf1c40f if is_promotion else 0xe74c3c

        await self.log_to_discord(
            f"{'UP' if is_promotion else 'DOWN'} Stage Change",
            f"**{old_stage}** -> **{new_stage}**",
            color=color,
            fields=[
                ("Date", now.strftime('%Y-%m-%d %H:%M'), True),
                ("Type", "Promotion" if is_promotion else "Demotion", True),
            ]
        )

    def queue_message(self, text: str):
        self.pending_messages.append(text)
        self.budget.record_received()
        self.add_message(self.name, text)
        log_message(self.display_name, "IN", text)

        if self.batch_timer_task and not self.batch_timer_task.done():
            self.batch_timer_task.cancel()

        self.batch_timer_task = asyncio.create_task(self._batch_wait())

    async def _batch_wait(self):
        try:
            await asyncio.sleep(90)
            await self.process_queued_messages()
        except asyncio.CancelledError:
            pass

    def _is_sleep_time(self) -> bool:
        hour = datetime.now(JST).hour
        return 0 <= hour < 7

    # ============================================================
    # FastAPI ルート
    # ============================================================
    def _setup_routes(self):
        bot = self

        @self.app.post("/callback")
        async def line_webhook(request: Request):
            body = await request.body()
            signature = request.headers.get("X-Line-Signature", "")

            if not await bot.verify_signature(body, signature):
                raise HTTPException(status_code=403, detail="Invalid signature")

            data = json.loads(body)
            for event in data.get("events", []):
                event_type = event.get("type", "")
                if event_type == "message":
                    msg = event["message"]
                    user_id = event["source"]["userId"]

                    if not bot.line_user_id:
                        bot._save_user_id(user_id)

                    if msg["type"] == "text":
                        text = msg["text"]
                        bot.logger.info(f"LINE received: {text[:50]}...")
                        asyncio.create_task(bot.notify_incoming_raw(text))
                        bot.queue_message(text)
                    elif msg["type"] in ("image", "video"):
                        label = "image" if msg["type"] == "image" else "video"
                        bot.add_message(bot.name, f"[{label}]")
                        log_media(bot.display_name, "IN", msg["type"])
                        asyncio.create_task(bot._forward_media(msg))
                    elif msg["type"] == "sticker":
                        pkg_id = msg.get("packageId", "?")
                        stk_id = msg.get("stickerId", "?")
                        text = f"[sticker (pkg:{pkg_id}, id:{stk_id})]"
                        bot.add_message(bot.name, text)
                        log_media(bot.display_name, "IN", "sticker")
                        bot.queue_message(text)
                    elif msg["type"] == "audio":
                        bot.add_message(bot.name, "[voice message]")
                        log_media(bot.display_name, "IN", "audio")
                        asyncio.create_task(bot._forward_media(msg))
                        bot.queue_message(f"[{bot.display_name} sent a voice message]")

                elif event_type == "follow":
                    bot._save_user_id(event["source"]["userId"])

            return {"status": "ok"}

        @self.app.get("/health")
        async def health():
            return {
                "status": "ok",
                "person": bot.display_name,
                "auto_respond": bot.auto_respond_enabled,
                "discord": bot.discord_client.is_ready(),
                "line_id": bool(bot.line_user_id),
                "budget": {
                    "monthly_sent": bot.budget.get_monthly_sent(),
                    "monthly_remaining": bot.budget.get_monthly_remaining(),
                    "daily_remaining": bot.budget.get_daily_remaining(),
                },
                "relationship_stage": bot.stage_manager.load_relationship(
                    bot.name, bot.display_name).get("stage", "unknown"),
                "time": datetime.now(JST).isoformat()
            }

    async def _forward_media(self, msg: dict):
        msg_type = msg["type"]
        message_id = msg["id"]
        if msg_type == "image":
            label = "image"
            emoji_icon = "IMG"
        elif msg_type == "video":
            label = "video"
            emoji_icon = "VID"
        elif msg_type == "audio":
            label = "audio"
            emoji_icon = "AUD"
        else:
            label = msg_type
            emoji_icon = "FILE"

        try:
            content_bytes, content_type = await self.download_line_content(message_id)
        except Exception as e:
            self.logger.error(f"Media download failed: {e}")
            return

        ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4", "audio/m4a": ".m4a"}
        default_ext = {"image": ".jpg", "video": ".mp4", "audio": ".m4a"}
        ext = ext_map.get(content_type, default_ext.get(msg_type, ".bin"))
        filename = f"{self.name}_{msg_type}_{message_id}{ext}"
        size_mb = len(content_bytes) / (1024 * 1024)

        await self.discord_ready.wait()
        channel = self.discord_client.get_channel(self.channel_id)
        if not channel:
            return

        now = datetime.now(JST)
        now_remote = now.astimezone(self.person_tz)
        time_str = f"{now.strftime('%H:%M')} JST / {now_remote.strftime('%H:%M')} {self.tz_label}"
        embed = Embed(title=f"📩 {self.display_name} ［{time_str}］", color=0xcc5de8)

        if size_mb > 8:
            embed.add_field(name=f"[{emoji_icon}] {label}", value=f"Too large: {size_mb:.1f}MB > 8MB", inline=False)
            await channel.send(embed=embed)
        else:
            embed.add_field(name=f"[{emoji_icon}] {label}", value=f"{size_mb:.1f}MB", inline=False)
            file = discord.File(io.BytesIO(content_bytes), filename=filename)
            if msg_type == "image":
                embed.set_image(url=f"attachment://{filename}")
            await channel.send(embed=embed, file=file)

    # ============================================================
    # プロアクティブ & Webhook 設定
    # ============================================================
    async def setup_line_webhook(self):
        import re
        for attempt in range(60):
            await asyncio.sleep(5)
            try:
                if self.tunnel_log.exists():
                    log_text = self.tunnel_log.read_text()
                    match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', log_text)
                    if match:
                        tunnel_url = match.group(0)
                        webhook_url = f"{tunnel_url}/callback"
                        async with httpx.AsyncClient() as client:
                            resp = await client.put(
                                'https://api.line.me/v2/bot/channel/webhook/endpoint',
                                headers={
                                    'Authorization': f'Bearer {self.line_access_token}',
                                    'Content-Type': 'application/json'
                                },
                                json={'endpoint': webhook_url}
                            )
                        if resp.status_code == 200:
                            self.logger.info(f"LINE Webhook set: {webhook_url}")
                            return
                        else:
                            self.logger.warning(f"LINE Webhook API error: {resp.status_code} {resp.text}")
            except Exception as e:
                self.logger.warning(f"Webhook setup attempt {attempt+1}: {e}")
        self.logger.error("Failed to set LINE Webhook after 60 attempts")

    async def proactive_check_loop(self):
        await self.discord_ready.wait()

        # proactive_messaging config
        pm_config = self.config.get('proactive_messaging', {})
        if not pm_config.get('enabled', True):
            self.logger.info("ProactiveScheduler disabled by config")
            return

        self.logger.info("ProactiveScheduler loop started")

        while True:
            try:
                await asyncio.sleep(3600)

                if not self.auto_respond_enabled:
                    continue

                if not self.budget.can_send():
                    continue

                profile = self.profile_learner.load_profile(self.name, self.display_name)
                rel = self.stage_manager.load_relationship(self.name, self.display_name)
                budget_info = {
                    'daily_remaining': self.budget.get_daily_remaining(),
                    'monthly_remaining': self.budget.get_monthly_remaining(),
                    'can_send': self.budget.can_send(),
                }

                result = await self.proactive_scheduler.check_and_initiate(
                    person_name=self.name,
                    config=self.config,
                    profile=profile,
                    relationship=rel,
                    budget=budget_info,
                    conversation_buffer=list(self.conversation_buffer),
                )

                if result and result.get('message'):
                    msg_text = result['message']
                    topic = result.get('topic', 'general')
                    reasoning = result.get('reasoning', 'proactive initiation')

                    success = await self.send_line_message(msg_text)
                    if success:
                        self.budget.record_sent()
                        self.add_message("you", msg_text)
                        log_message(self.display_name, "OUT", msg_text,
                                    metadata={"source": "プロアクティブ", "reasoning": reasoning[:100]})
                        pro_translation = ""
                        try:
                            pro_translation = await self.translate_to_japanese([msg_text])
                        except Exception:
                            pass
                        await self.log_outgoing(msg_text, f"Proactive: {reasoning}",
                                           delay_min=0,
                                           topic_tags=[topic],
                                           push_pull_action="push",
                                           translation=pro_translation)
                        self.logger.info(f"Proactive message sent: {msg_text[:50]}...")

            except Exception as e:
                self.logger.error(f"Proactive check error: {e}")

    # ============================================================
    # メインエントリーポイント
    # ============================================================
    async def run(self):
        config = uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="info")
        server = uvicorn.Server(config)

        rel = self.stage_manager.load_relationship(self.name, self.display_name)
        current_stage = rel.get('stage', 'friends')

        self.logger.info(f"Starting {self.display_name} Auto Bot on port {self.port}")
        self.logger.info(f"Discord channel: {self.channel_id}")
        self.logger.info(f"Auto-respond: {self.auto_respond_enabled}")
        self.logger.info(f"Budget: {self.budget.get_monthly_remaining()}/{MONTHLY_LIMIT} remaining")
        self.logger.info(f"Stage: {current_stage}")
        self.logger.info(f"Relationship Engine: all components loaded")

        await asyncio.gather(
            self.discord_client.start(self.discord_token),
            server.serve(),
            self.setup_line_webhook(),
            self.proactive_check_loop(),
            self.check_unanswered_on_startup(),
        )

    async def check_unanswered_on_startup(self):
        """起動時に未返信メッセージを検出し、自動処理する"""
        await self.discord_ready.wait()
        await asyncio.sleep(10)  # 他の初期化完了を待つ

        if not self.auto_respond_enabled:
            return

        buf = list(self.conversation_buffer)
        if not buf:
            return

        # 末尾から連続する相手メッセージを収集
        unanswered = []
        for msg in reversed(buf):
            if msg.get('role') == 'you':
                break
            unanswered.insert(0, msg.get('text', ''))

        if not unanswered:
            self.logger.info("Startup check: no unanswered messages")
            return

        self.logger.info(f"Startup check: {len(unanswered)} unanswered message(s) found")

        # sleep時間中なら朝まで待機
        if self._is_sleep_time():
            now = datetime.now(JST)
            wake_time = now.replace(hour=7, minute=random.randint(5, 30), second=0)
            if wake_time <= now:
                wake_time += timedelta(days=1)
            delay = int((wake_time - now).total_seconds())
            self.logger.info(f"Startup check: sleep time, scheduling for {delay // 60}min later")
            asyncio.create_task(self.delayed_respond(unanswered, delay))
            return

        # 朝なのに未返信 → 短いランダム遅延で返信
        delay = random.randint(60, 300)  # 1-5分
        self.logger.info(f"Startup check: responding in {delay // 60}min")
        asyncio.create_task(self.delayed_respond(unanswered, delay))


# ============================================================
# AutoRespondToggleView (botインスタンスへの参照を持つ)
# ============================================================
class AutoRespondToggleView(ui.View):
    def __init__(self, bot: AutoChatBot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label='自動応答 停止', style=ButtonStyle.red, custom_id='toggle_auto')
    async def toggle(self, interaction: discord.Interaction, button: ui.Button):
        self.bot.auto_respond_enabled = not self.bot.auto_respond_enabled
        if self.bot.auto_respond_enabled:
            button.label = '自動応答 停止'
            button.style = ButtonStyle.red
            await interaction.response.send_message("自動応答を再開しました", ephemeral=True)
        else:
            button.label = '自動応答 再開'
            button.style = ButtonStyle.green
            await interaction.response.send_message(
                f"自動応答を停止しました。このチャンネルに入力すると{self.bot.display_name}に直接送信されます。",
                ephemeral=True)
        await interaction.message.edit(view=self)


# ============================================================
# メッセージ予算管理
# ============================================================
class MessageBudget:
    def __init__(self, budget_file: Path):
        self.budget_file = budget_file
        self.data = self._load()

    def _load(self) -> dict:
        if self.budget_file.exists():
            try:
                return json.loads(self.budget_file.read_text())
            except Exception:
                pass
        now = datetime.now(JST)
        return {
            "month": now.strftime('%Y-%m'),
            "monthly_sent": 0,
            "daily_log": {}
        }

    def _save(self):
        self.budget_file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))

    def _check_month_reset(self):
        now = datetime.now(JST)
        current_month = now.strftime('%Y-%m')
        if self.data["month"] != current_month:
            self.data = {
                "month": current_month,
                "monthly_sent": 0,
                "daily_log": {}
            }
            self._save()

    def _today_key(self) -> str:
        return datetime.now(JST).strftime('%Y-%m-%d')

    def get_today_sent(self) -> int:
        self._check_month_reset()
        return self.data["daily_log"].get(self._today_key(), {}).get("sent", 0)

    def get_monthly_sent(self) -> int:
        self._check_month_reset()
        return self.data["monthly_sent"]

    def get_monthly_remaining(self) -> int:
        return max(0, MONTHLY_LIMIT - self.get_monthly_sent())

    def get_yesterday_sent(self) -> int:
        yesterday = (datetime.now(JST) - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.data["daily_log"].get(yesterday, {}).get("sent", 0)

    def calculate_daily_budget(self) -> int:
        self._check_month_reset()
        today = self._today_key()

        # Use cached budget for today if already calculated
        cached = self.data["daily_log"].get(today, {}).get("budget")
        if cached is not None:
            return cached

        now = datetime.now(JST)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        remaining_days = max(1, days_in_month - now.day + 1)
        effective_limit = MONTHLY_LIMIT - RESERVE
        remaining = max(0, effective_limit - self.data["monthly_sent"])

        if remaining <= 0:
            return 0

        base = remaining / remaining_days

        dow_factor = {
            0: 0.9, 1: 0.85, 2: 0.85, 3: 0.9,
            4: 1.1, 5: 1.25, 6: 1.15,
        }[now.weekday()]

        yesterday = self.get_yesterday_sent()
        if yesterday > base * 1.5:
            momentum = 0.75
        elif yesterday == 0:
            momentum = 1.15
        else:
            momentum = 1.0

        jitter = random.uniform(0.75, 1.25)

        budget = base * dow_factor * momentum * jitter
        budget = max(2, min(12, round(budget)))

        if remaining <= 10:
            budget = min(budget, 1)
        elif remaining <= 25:
            budget = min(budget, 3)

        # Cache budget for today
        if today not in self.data["daily_log"]:
            self.data["daily_log"][today] = {"sent": 0, "received": 0, "budget": budget}
        else:
            self.data["daily_log"][today]["budget"] = budget
        self._save()

        return budget

    def get_daily_remaining(self) -> int:
        budget = self.calculate_daily_budget()
        sent = self.get_today_sent()
        return max(0, budget - sent)

    def record_sent(self):
        self._check_month_reset()
        today = self._today_key()
        self.data["monthly_sent"] += 1
        if today not in self.data["daily_log"]:
            self.data["daily_log"][today] = {"sent": 0, "received": 0, "budget": self.calculate_daily_budget()}
        self.data["daily_log"][today]["sent"] += 1
        self._save()

    def record_received(self):
        self._check_month_reset()
        today = self._today_key()
        if today not in self.data["daily_log"]:
            self.data["daily_log"][today] = {"sent": 0, "received": 0, "budget": self.calculate_daily_budget()}
        self.data["daily_log"][today]["received"] += 1
        self._save()

    def can_send(self) -> bool:
        return self.get_daily_remaining() > 0 and self.get_monthly_remaining() > 0


# ============================================================
# 共通フォーマッタ
# ============================================================
EMOTION_ANALYSIS_PROMPT = """Analyze the emotional state of the person who sent the following message(s).
This is a casual LINE chat between friends who are getting to know each other.

Return ONLY valid JSON (no markdown, no code blocks, no explanation):
{{
  "scores": {{
    "mood": <1-10>,
    "energy": <1-10>,
    "intimacy": <1-10>,
    "longing": <1-10>,
    "playfulness": <1-10>,
    "engagement": <1-10>
  }},
  "attachment": "safe|anxious|avoidant",
  "risk": "none|minor|caution|danger",
  "note": "Brief observation about emotional state (Japanese, max 50 chars)",
  "reply_decision": {{
    "message_type": "question|emotional_sharing|daily_sharing|reaction|farewell|other",
    "silence_risk": "high|medium|low|none",
    "reasoning": "Why reply is or isn't needed (English, max 30 chars)"
  }}
}}

Scoring guide:
- mood: 1=very negative/upset, 5=neutral, 10=very happy/positive
- energy: 1=low energy/tired/subdued, 5=normal, 10=very excited/enthusiastic
- intimacy: 1=distant/surface level, 5=friendly, 10=deep emotional sharing/vulnerability
- longing: 1=neutral/indifferent, 5=warm, 10=intense missing/wanting/affection
- playfulness: 1=serious/flat, 5=normal, 10=very joking/teasing/flirty
- engagement: 1=minimal/one-word responses, 5=normal conversation, 10=deeply invested/long messages

Risk assessment:
- none: Normal conversation
- minor: Slight signs of discomfort or pulling away
- caution: Clear signs of upset, frustration, or emotional withdrawal
- danger: Anger, blocking signals, or explicit negative feedback

Attachment style:
- safe: Comfortable, balanced communication
- anxious: Seeking validation, frequent messaging, worry about responses
- avoidant: Short replies, deflecting deep topics, pulling away

Reply decision guide:
- message_type: What kind of message is this?
  - question: Direct question requiring an answer
  - emotional_sharing: Sharing feelings, venting, seeking empathy
  - daily_sharing: Sharing daily activities, updates, small talk
  - reaction: Short reactions like "haha", "ok", "nice", emoji-only
  - farewell: Goodbye, goodnight, talk later
  - other: Anything else
- silence_risk: What happens if we DON'T reply?
  - high: Ignoring would damage the relationship (unanswered question, ignored emotions, ignored bid for connection)
  - medium: Reply is expected but silence won't cause damage (daily sharing, casual update)
  - low: Silence is natural here (mutual reactions exchanged, conversation winding down)
  - none: Silence is preferred (after goodbye, conversation clearly ended)

Messages to analyze:
{messages}"""


SCORE_LABELS_JA = {
    "mood": "気分　　　",
    "energy": "テンション",
    "intimacy": "親密度　　",
    "longing": "甘え　　　",
    "playfulness": "遊び心　　",
    "engagement": "エンゲージ",
}

DELTA_LABELS_JA = {
    "mood": "気分",
    "energy": "テンション",
    "intimacy": "親密度",
    "longing": "甘え",
    "playfulness": "遊び心",
    "engagement": "エンゲージ",
}


def format_emotion_bars(scores: dict) -> str:
    labels = [
        ("mood", "気分　　　"),
        ("energy", "テンション"),
        ("intimacy", "親密度　　"),
        ("longing", "甘え　　　"),
        ("playfulness", "遊び心　　"),
        ("engagement", "エンゲージ"),
    ]
    lines = []
    for key, label in labels:
        val = scores.get(key, 5)
        bar = "█" * val + "░" * (10 - val)
        lines.append(f"{label} {bar} {val}")
    return "\n".join(lines)


def format_attachment_risk(attachment: str, risk: str) -> str:
    att_map = {"safe": "🟢安全", "anxious": "🟡不安", "avoidant": "🔴回避"}
    risk_map = {"none": "なし", "minor": "軽微", "caution": "⚠️ 警戒", "danger": "🚨 危険"}
    return (f"愛着: {att_map.get(attachment, attachment)}  "
            f"危険信号: {risk_map.get(risk, risk)}")


# ============================================================
# エントリーポイント
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Auto Chat Bot (Relationship Engine)')
    parser.add_argument('--config', required=True, help='Path to config JSON file')
    args = parser.parse_args()

    config = load_config(args.config)
    bot = AutoChatBot(config)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
