#!/usr/bin/env python3
"""
collect_discord_logs.py — Discord チャンネルから過去の全会話ログを収集

Discord REST API でメッセージを全件取得し、Embed を解析して
chat_logs/{name}/YYYY-MM-DD.md に保存する。

使い方:
  python3 collect_discord_logs.py --name laura --channel 1470618070329327784 --token BOT_TOKEN
  python3 collect_discord_logs.py --name aljela --channel 1470995067492761712 --token BOT_TOKEN
"""

import argparse
import json
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

JST = ZoneInfo("Asia/Tokyo")
LOG_DIR = Path(__file__).parent / "chat_logs"
API_BASE = "https://discord.com/api/v10"


def load_env():
    """Load .env file"""
    env = {}
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip()
    return env


def fetch_all_messages(channel_id: str, token: str) -> list[dict]:
    """Discord REST API で全メッセージを取得（ページネーション対応）"""
    headers = {"Authorization": f"Bot {token}"}
    all_messages = []
    before = None
    page = 0

    with httpx.Client(timeout=30) as client:
        while True:
            url = f"{API_BASE}/channels/{channel_id}/messages?limit=100"
            if before:
                url += f"&before={before}"

            resp = client.get(url, headers=headers)

            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                print(f"  Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            messages = resp.json()

            if not messages:
                break

            all_messages.extend(messages)
            before = messages[-1]["id"]
            page += 1
            print(f"  Page {page}: fetched {len(messages)} messages (total: {len(all_messages)})")

            if len(messages) < 100:
                break

            time.sleep(0.5)  # Rate limit 回避

    # 古い順にソート
    all_messages.reverse()
    return all_messages


def parse_laura_embed(embed: dict) -> dict | None:
    """Laura Bot の Embed を解析して会話データを抽出"""
    title = embed.get("title", "")
    description = embed.get("description", "")
    fields = {f["name"]: f["value"] for f in embed.get("fields", [])}

    # 受信メッセージ: 📩 Laura [HH:MM JST / HH:MM CET]
    if title.startswith("📩 Laura"):
        original = fields.get("🇬🇧 原文", "").lstrip("> ").strip()
        translation = fields.get("🇯🇵 日本語訳", "").strip()
        emotion = fields.get("📊 感情分析", "").strip("`\n ")
        note = fields.get("📝 補足", "").strip()

        if original:
            metadata = {}
            if emotion:
                metadata["感情"] = emotion.replace("\n", " | ")
            if note:
                metadata["補足"] = note
            return {
                "direction": "IN",
                "message": translation or original,
                "original": original,
                "metadata": metadata if metadata else None,
            }

    # 送信メッセージ: ✅ Lauraに送信しました
    if "✅ Lauraに送信しました" in description or "✅ Laura" in description:
        lines = description.split("\n")
        ja_text = ""
        en_text = ""
        for line in lines:
            line = line.strip()
            if line.startswith("🇯🇵"):
                ja_text = line.replace("🇯🇵", "").strip()
            elif line.startswith("🇬🇧"):
                en_text = line.replace("🇬🇧", "").strip()

        if en_text:
            return {
                "direction": "OUT",
                "message": en_text,
                "original": ja_text if ja_text else None,
                "metadata": None,
            }

    # 画像/動画: 📩 Laura [time] with 🖼️/🎬 field
    if title.startswith("📩 Laura"):
        for fname, fval in fields.items():
            if "🖼️" in fname or "画像" in fname:
                return {"direction": "IN", "message": "[📷 画像]", "original": None, "metadata": None}
            if "🎬" in fname or "動画" in fname:
                return {"direction": "IN", "message": "[🎬 動画]", "original": None, "metadata": None}

    return None


def parse_auto_bot_embed(embed: dict, display_name: str) -> dict | None:
    """Auto Bot の Embed を解析して会話データを抽出"""
    title = embed.get("title", "")
    description = embed.get("description", "")
    fields = {f["name"]: f["value"] for f in embed.get("fields", [])}

    # 受信: IN {Name} [HH:MM JST / HH:MM TZ]
    if title.startswith(f"IN {display_name}"):
        # description contains the messages as "> text" lines
        messages = []
        for line in description.split("\n"):
            line = line.strip()
            if line.startswith(">"):
                messages.append(line.lstrip("> ").strip())

        if messages:
            msg_text = "\n".join(messages)
            metadata = {}
            if "Emotion" in fields:
                metadata["感情"] = fields["Emotion"].strip("`\n ")[:100]
            if "Strategy" in fields:
                metadata["戦略"] = fields["Strategy"][:100]
            if "Stage" in fields:
                metadata["ステージ"] = fields["Stage"]
            return {
                "direction": "IN",
                "message": msg_text,
                "original": None,
                "metadata": metadata if metadata else None,
            }

    # 送信: OUT You -> {Name} [HH:MM JST / HH:MM TZ]
    if title.startswith(f"OUT You -> {display_name}") or title.startswith("OUT You ->"):
        msg = description.lstrip("> ").strip()
        if msg:
            metadata = {}
            if "Reasoning" in fields:
                metadata["理由"] = fields["Reasoning"][:100]
            if "Push/Pull" in fields:
                metadata["Push/Pull"] = fields["Push/Pull"]
            return {
                "direction": "OUT",
                "message": msg,
                "original": None,
                "metadata": metadata if metadata else None,
            }

    # スキップ: SKIP [time]
    if title.startswith("SKIP"):
        return {
            "direction": "SYSTEM",
            "message": f"[応答スキップ] {description}",
            "original": None,
            "metadata": None,
        }

    # ステージ変更
    if "Stage Change" in title:
        return {
            "direction": "SYSTEM",
            "message": f"[ステージ変更] {description}",
            "original": None,
            "metadata": None,
        }

    return None


def save_logs(name: str, entries: list[tuple[datetime, dict]]):
    """日付別にログを保存"""
    by_date = defaultdict(list)
    for ts, entry in entries:
        date_str = ts.strftime("%Y-%m-%d")
        by_date[date_str].append((ts, entry))

    log_dir = LOG_DIR / name.lower()
    log_dir.mkdir(parents=True, exist_ok=True)

    total_msgs = 0
    for date_str, day_entries in sorted(by_date.items()):
        log_file = log_dir / f"{date_str}.md"

        lines = [f"# {name} — {date_str}\n\n"]

        for ts, entry in day_entries:
            time_str = ts.strftime("%H:%M:%S")
            direction = entry["direction"]

            if direction == "IN":
                arrow = f"**{name} →**"
            elif direction == "OUT":
                arrow = f"**→ {name}**"
            else:
                arrow = "**⚙️ System**"

            lines.append(f"### [{time_str}] {arrow}\n")
            lines.append(f"{entry['message']}\n")

            if entry.get("original") and entry["original"] != entry["message"]:
                lines.append(f"> 原文: {entry['original']}\n")

            if entry.get("metadata"):
                meta_parts = []
                for k, v in entry["metadata"].items():
                    if v:
                        meta_parts.append(f"*{k}: {v}*")
                if meta_parts:
                    lines.append(" | ".join(meta_parts) + "\n")

            lines.append("---\n")

        with open(log_file, "w") as f:
            f.write("\n".join(lines))

        total_msgs += len(day_entries)
        print(f"  {date_str}: {len(day_entries)} messages")

    return len(by_date), total_msgs


def main():
    parser = argparse.ArgumentParser(description="Collect Discord chat logs")
    parser.add_argument("--name", required=True, help="Person name (laura, aljela, michelle...)")
    parser.add_argument("--channel", required=True, help="Discord channel ID")
    parser.add_argument("--token", help="Discord bot token (or reads from .env)")
    parser.add_argument("--display-name", help="Display name for auto bot parsing (default: capitalized name)")
    parser.add_argument("--bot-type", choices=["laura", "auto"], default="auto",
                        help="Bot type for embed parsing (laura=semi-auto, auto=full-auto)")
    args = parser.parse_args()

    # トークン取得
    token = args.token
    if not token:
        env = load_env()
        token = env.get("DISCORD_TOKEN")
        if not token:
            print("Error: --token required or DISCORD_TOKEN in .env")
            return

    display_name = args.display_name or args.name.capitalize()

    print(f"Collecting logs for {args.name} from channel {args.channel}...")
    print(f"Bot type: {args.bot_type}, Display name: {display_name}")

    # 全メッセージ取得
    messages = fetch_all_messages(args.channel, token)
    print(f"\nTotal messages fetched: {len(messages)}")

    # Embed 解析
    entries = []
    skipped = 0
    for msg in messages:
        # メッセージのタイムスタンプ（ISO 8601）
        ts_str = msg.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("+00:00", "+00:00"))
            ts = ts.astimezone(JST)
        except (ValueError, TypeError):
            continue

        # Embed を解析
        embeds = msg.get("embeds", [])
        if not embeds:
            # Embed なしの普通のテキストメッセージ（手動メッセージ等）
            content = msg.get("content", "").strip()
            if content and not msg.get("author", {}).get("bot", False):
                entries.append((ts, {
                    "direction": "OUT",
                    "message": content,
                    "original": None,
                    "metadata": {"source": "手動送信"},
                }))
            continue

        for embed in embeds:
            if args.bot_type == "laura":
                parsed = parse_laura_embed(embed)
            else:
                parsed = parse_auto_bot_embed(embed, display_name)

            if parsed:
                entries.append((ts, parsed))
            else:
                skipped += 1

    print(f"Parsed: {len(entries)} entries, Skipped: {skipped} embeds")

    if not entries:
        print("No conversation entries found.")
        return

    # 保存
    print(f"\nSaving to chat_logs/{args.name.lower()}/...")
    days, total = save_logs(args.name, entries)
    print(f"\nDone: {total} messages across {days} days")


if __name__ == "__main__":
    main()
