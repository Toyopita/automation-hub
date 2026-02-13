#!/usr/bin/env python3
"""Biweekly strategy report generator for all LINE bots.

Analyzes conversation history, profiles, relationship stages, emotion trends,
and budget usage. Posts detailed report to Discord #strategy-report channel.
"""

import asyncio
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

JST = ZoneInfo('Asia/Tokyo')
BASE_DIR = Path(__file__).parent
CLAUDE_CLI = '/Users/minamitakeshi/.local/bin/claude'

# Load .env manually
env_path = BASE_DIR / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')
REPORT_CHANNEL_ID = os.environ.get('STRATEGY_REPORT_CHANNEL_ID', '')

BOTS = [
    {'name': 'michelle', 'display': 'Michelle'},
    {'name': 'vita', 'display': 'Vita'},
    {'name': 'gift_ars', 'display': 'Gift_ars'},
    {'name': 'grayi', 'display': 'Grayi'},
    {'name': 'aljela', 'display': 'Suraya'},
]


def load_json(path: Path, default=None):
    if not path.exists():
        return default or {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default or {}


def gather_bot_data(bot: dict) -> dict:
    """Gather all data for a single bot."""
    name = bot['name']
    config = load_json(BASE_DIR / f'{name}_config.json')
    profile = load_json(BASE_DIR / f'{name}_profile.json')
    relationship = load_json(BASE_DIR / f'{name}_relationship.json')
    budget = load_json(BASE_DIR / f'{name}_budget.json')
    buffer_path = BASE_DIR / f'.{name}_conversation_buffer.json'
    buffer = load_json(buffer_path, default=[])
    emotion_path = BASE_DIR / f'{name}_emotion_data.json'
    emotion_data = load_json(emotion_path, default=[])

    # Recent conversation summary (last 20 messages)
    recent_msgs = buffer[-20:] if isinstance(buffer, list) else []

    # Count messages per role
    their_msgs = [m for m in buffer if m.get('role') == name]
    our_msgs = [m for m in buffer if m.get('role') == 'you']

    # Recent emotion scores (last 5)
    recent_emotions = []
    if isinstance(emotion_data, list):
        recent_emotions = emotion_data[-5:]
    elif isinstance(emotion_data, dict) and 'entries' in emotion_data:
        recent_emotions = emotion_data['entries'][-5:]

    return {
        'name': name,
        'display': bot['display'],
        'config': config,
        'profile': profile,
        'relationship': relationship,
        'budget': budget,
        'buffer': recent_msgs,
        'total_their_msgs': len(their_msgs),
        'total_our_msgs': len(our_msgs),
        'total_msgs': len(buffer),
        'recent_emotions': recent_emotions,
        'stage': relationship.get('stage', 'unknown'),
    }


def build_analysis_prompt(all_data: list[dict]) -> str:
    """Build the prompt for Claude to analyze."""
    now = datetime.now(JST)

    sections = []
    for d in all_data:
        config = d['config']
        profile = d['profile']

        # Format conversation
        conv_lines = []
        for m in d['buffer']:
            role_label = d['display'] if m.get('role') == d['name'] else 'YOU'
            conv_lines.append(f"[{m.get('time', '?')}] {role_label}: {m.get('text', '')}")
        conv_text = '\n'.join(conv_lines) if conv_lines else '(No conversation yet)'

        # Format profile facts
        facts = profile.get('facts', {})
        facts_text = json.dumps(facts, ensure_ascii=False, indent=1) if facts else '(No facts collected yet)'

        # Emotion trend
        emotion_lines = []
        for e in d['recent_emotions']:
            scores = e.get('scores', e) if isinstance(e, dict) else {}
            if isinstance(scores, dict):
                emotion_lines.append(str({k: v for k, v in scores.items()
                                         if k in ('mood', 'engagement', 'intimacy', 'longing', 'playfulness')}))

        section = f"""
### {d['display']} ({d['name']})
- **Stage**: {d['stage']}
- **Background**: {config.get('background', 'N/A')}
- **Strategy**: {config.get('strategy_direction', 'N/A')}
- **Total messages**: {d['total_msgs']} (theirs: {d['total_their_msgs']}, ours: {d['total_our_msgs']})
- **Budget**: Monthly sent: {d['budget'].get('monthly_sent', 0)}/200
- **Profile facts**: {facts_text}
- **Recent emotion scores**: {chr(10).join(emotion_lines) if emotion_lines else '(none)'}
- **Recent conversation**:
```
{conv_text}
```
"""
        sections.append(section)

    prompt = f"""You are a dating strategy analyst. Analyze the following data for 5 women being pursued through LINE messaging bots. All were met on Langmate (language exchange app). The user lives in Osaka, Japan.

Today: {now.strftime('%Y-%m-%d %H:%M JST')}

GOALS:
- Start dating each person
- Develop intimate online chat relationships
- Be strategic but natural, match each person's pace

DATA:
{''.join(sections)}

Generate a DETAILED biweekly strategy report in Japanese. Structure:

## 📊 全体サマリー
- 全体の進捗状況
- 最も有望な相手
- 注意が必要な相手

## 📋 個別レポート（各人）
For each person:
### [名前]
**現状分析:**
- 関係の現在地（友達/興味あり/脈あり等）
- 収集済み情報（彼氏有無、タイプ、仕事、趣味等）
- 未収集の重要情報
- 感情傾向（engagement, intimacy等のトレンド）

**評価:**
- 脈あり度: ★☆☆☆☆ 〜 ★★★★★
- 進展速度: 速い/普通/遅い
- リスク要因: (あれば)

**次の2週間のアクションプラン:**
- 具体的に何を聞くべきか
- どういう方向に会話を持っていくか
- 避けるべきこと

## 🎯 優先順位
- 今後2週間で最も注力すべき相手とその理由

Be specific, actionable, and honest about chances. Write in Japanese.
"""
    return prompt


async def call_claude(prompt: str) -> str:
    """Call Claude CLI for analysis."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                     encoding='utf-8', dir='/tmp') as f:
        f.write(prompt)
        tmp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            '/bin/bash', '-c',
            f'cd /tmp && cat "{tmp_path}" | {CLAUDE_CLI} --print '
            f'--model claude-sonnet-4-5-20250929 '
            f'--system-prompt "You are a dating strategy analyst. Output in Japanese."',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    output = stdout.decode('utf-8').strip()
    if not output:
        raise RuntimeError(f"Claude returned empty. stderr: {stderr.decode()[:300]}")
    return output


async def post_to_discord(content: str):
    """Post report to Discord, splitting if needed (2000 char limit per message)."""
    if not DISCORD_TOKEN or not REPORT_CHANNEL_ID:
        print("ERROR: DISCORD_TOKEN or STRATEGY_REPORT_CHANNEL_ID not set")
        return

    # Split content into chunks of max 1900 chars (leave margin)
    chunks = []
    current = ""
    for line in content.split('\n'):
        if len(current) + len(line) + 1 > 1900:
            chunks.append(current)
            current = line
        else:
            current += ('\n' if current else '') + line
    if current:
        chunks.append(current)

    async with httpx.AsyncClient() as client:
        for i, chunk in enumerate(chunks):
            resp = await client.post(
                f'https://discord.com/api/v10/channels/{REPORT_CHANNEL_ID}/messages',
                headers={
                    'Authorization': f'Bot {DISCORD_TOKEN}',
                    'Content-Type': 'application/json',
                },
                json={'content': chunk}
            )
            if resp.status_code != 200:
                print(f"Discord post failed (chunk {i+1}): {resp.status_code} {resp.text}")
            else:
                print(f"Posted chunk {i+1}/{len(chunks)}")
            await asyncio.sleep(1)  # Rate limit


async def main():
    print(f"=== Biweekly Report Generator ===")
    now = datetime.now(JST)
    print(f"Time: {now.isoformat()}")

    # Biweekly check: run on even ISO week numbers only
    # (launchd runs weekly, we skip odd weeks)
    week_num = now.isocalendar()[1]
    if '--force' not in __import__('sys').argv and week_num % 2 != 0:
        print(f"Skipping: week {week_num} is odd (runs on even weeks). Use --force to override.")
        return

    # 1. Gather data
    all_data = []
    for bot in BOTS:
        data = gather_bot_data(bot)
        print(f"  {bot['display']}: {data['total_msgs']} msgs, stage={data['stage']}")
        all_data.append(data)

    # 2. Build prompt and call Claude
    prompt = build_analysis_prompt(all_data)
    print(f"\nCalling Claude for analysis...")
    report = await call_claude(prompt)
    print(f"Report generated: {len(report)} chars")

    # 3. Add header
    now = datetime.now(JST)
    header = f"# 📊 隔週戦略レポート\n**{now.strftime('%Y年%m月%d日 %H:%M')} JST**\n\n"
    full_report = header + report

    # 4. Post to Discord
    print(f"\nPosting to Discord...")
    await post_to_discord(full_report)
    print("Done!")


if __name__ == '__main__':
    asyncio.run(main())
