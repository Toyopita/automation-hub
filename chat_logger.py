#!/usr/bin/env python3
"""
chat_logger.py — 会話ログの永続保存モジュール

全Bot共通で使用。メッセージを日付別マークダウンファイルに追記する。
保存先: chat_logs/{person_name}/YYYY-MM-DD.md
"""

import fcntl
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
LOG_DIR = Path(__file__).parent / "chat_logs"


def log_message(
    person_name: str,
    direction: str,
    message: str,
    original: str = None,
    metadata: dict = None,
    timestamp: datetime = None,
):
    """
    会話ログを日付別ファイルに追記する。

    Args:
        person_name: 相手の名前（ディレクトリ名になる）
        direction: "IN" (相手から受信) or "OUT" (相手へ送信)
        message: メッセージ本文
        original: 翻訳前の原文（あれば）
        metadata: 追加情報 dict（感情分析、戦略等）
        timestamp: タイムスタンプ（省略時は現在時刻）
    """
    now = timestamp or datetime.now(JST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=JST)
    else:
        now = now.astimezone(JST)

    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    log_dir = LOG_DIR / person_name.lower()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date_str}.md"

    # ログエントリ構築
    if direction == "IN":
        arrow = f"**{person_name} →**"
    else:
        arrow = f"**→ {person_name}**"

    lines = [f"### [{time_str}] {arrow}", ""]

    if original and original != message:
        # 翻訳ありの場合: 原文と翻訳を両方表示
        lines.append(f"{message}")
        lines.append("")
        lines.append(f"> 原文: {original}")
    else:
        lines.append(f"{message}")

    lines.append("")

    if metadata:
        meta_parts = []
        for key, value in metadata.items():
            if value:
                meta_parts.append(f"*{key}: {value}*")
        if meta_parts:
            lines.append(" | ".join(meta_parts))
            lines.append("")

    lines.append("---")
    lines.append("")

    entry = "\n".join(lines)

    # ファイルロック付きで追記
    is_new = not log_file.exists()
    with open(log_file, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            if is_new:
                f.write(f"# {person_name} — {date_str}\n\n")
            f.write(entry)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def log_media(
    person_name: str,
    direction: str,
    media_type: str,
    filename: str = None,
    timestamp: datetime = None,
):
    """画像・動画・スタンプ・音声メッセージのログ"""
    label_map = {
        "image": "📷 画像",
        "video": "🎬 動画",
        "sticker": "🎭 スタンプ",
        "audio": "🎤 ボイスメッセージ",
    }
    label = label_map.get(media_type, f"📎 {media_type}")
    text = f"[{label}]"
    if filename:
        text += f" {filename}"
    log_message(person_name, direction, text, timestamp=timestamp)


def log_system(
    person_name: str,
    event: str,
    detail: str = "",
    timestamp: datetime = None,
):
    """システムイベントのログ（ステージ変更、プロアクティブ等）"""
    now = timestamp or datetime.now(JST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=JST)
    else:
        now = now.astimezone(JST)

    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    log_dir = LOG_DIR / person_name.lower()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date_str}.md"

    entry = f"### [{time_str}] ⚙️ {event}\n\n"
    if detail:
        entry += f"{detail}\n\n"
    entry += "---\n\n"

    is_new = not log_file.exists()
    with open(log_file, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            if is_new:
                f.write(f"# {person_name} — {date_str}\n\n")
            f.write(entry)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
