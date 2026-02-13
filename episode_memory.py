#!/usr/bin/env python3
"""
Episode Memory - Long-term conversation memory through compression.

When the conversation buffer overflows, older messages are compressed into
episode summaries that persist indefinitely. This prevents complete loss
of context when the 30-message buffer wraps around.

Episodes are stored in {name}_episodes.json.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger('episode_memory')

BASE_DIR = Path(__file__).parent
JST = ZoneInfo('Asia/Tokyo')


def _episodes_path(name: str) -> Path:
    return BASE_DIR / f'{name}_episodes.json'


def load_episodes(name: str) -> list[dict]:
    """Load episodes from disk."""
    path = _episodes_path(name)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('episodes', [])
        return []
    except Exception as e:
        logger.warning(f"Failed to load episodes for {name}: {e}")
        return []


def save_episodes(name: str, episodes: list[dict]):
    """Save episodes to disk atomically."""
    path = _episodes_path(name)
    tmp = path.with_suffix('.tmp')
    try:
        tmp.write_text(
            json.dumps(episodes, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        tmp.replace(path)
    except Exception as e:
        logger.error(f"Failed to save episodes for {name}: {e}")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


async def compress_to_episode(messages: list[dict], name: str,
                               display_name: str,
                               model: str = 'claude-sonnet-4-5-20250929') -> dict | None:
    """Compress a batch of messages into an episode summary.

    Args:
        messages: List of conversation buffer entries (role, text, time).
        name: Person identifier for file storage.
        display_name: Human-readable name for prompts.
        model: Claude model to use.

    Returns:
        Episode dict or None on failure.
    """
    if not messages:
        return None

    from relationship_engine import _call_claude_json

    # Build conversation text
    conv_lines = []
    for m in messages:
        role = display_name if m.get('role') != 'you' else 'YOU'
        time_str = m.get('time', '')
        text = m.get('text', '')
        conv_lines.append(f"[{time_str}] {role}: {text}")

    conversation_text = "\n".join(conv_lines)

    # Extract time range
    times = [m.get('time', '') for m in messages if m.get('time')]
    ts_start = times[0] if times else datetime.now(JST).strftime('%Y-%m-%d %H:%M')
    ts_end = times[-1] if times else ts_start

    prompt = f"""Compress this conversation segment into an episode summary.

Conversation between YOU and {display_name}:
{conversation_text}

Return JSON:
{{
  "summary": "2-3 sentence summary of what happened in this conversation",
  "topics": ["topic1", "topic2"],
  "key_facts_learned": ["new facts learned about {display_name}, if any"],
  "emotional_tone": "brief description of the emotional tone",
  "unresolved": "anything left unfinished or promised (null if nothing)"
}}

Rules:
- summary should capture the KEY moments, not every detail
- topics: 2-5 topic tags
- key_facts_learned: only NEW information about {display_name}. Empty array if nothing new.
- emotional_tone: 3-5 words describing the overall mood
- unresolved: things she said she'd do, or questions left unanswered
- Return ONLY valid JSON"""

    system = ("You are a conversation summarizer. Compress chat logs into concise episode summaries. "
              "Focus on what matters for continuing the relationship. Return ONLY valid JSON.")

    try:
        result = await _call_claude_json(prompt, system, model=model)
    except Exception as e:
        logger.error(f"Episode compression failed for {name}: {e}")
        return None

    # Assign episode ID
    episodes = load_episodes(name)
    next_id = (episodes[-1].get('id', 0) + 1) if episodes else 1

    episode = {
        'id': next_id,
        'timestamp_start': ts_start,
        'timestamp_end': ts_end,
        'summary': result.get('summary', ''),
        'topics': result.get('topics', []),
        'key_facts_learned': result.get('key_facts_learned', []),
        'emotional_tone': result.get('emotional_tone', ''),
        'unresolved': result.get('unresolved'),
    }

    episodes.append(episode)

    # Recompress if too many episodes
    if len(episodes) > 50:
        episodes = await _recompress_old_episodes(episodes, name, display_name, model)

    save_episodes(name, episodes)
    logger.info(f"Episode {next_id} created for {name}: {episode['summary'][:60]}...")
    return episode


async def _recompress_old_episodes(episodes: list[dict], name: str,
                                     display_name: str,
                                     model: str) -> list[dict]:
    """When episodes exceed 50, compress the oldest 5 into 1."""
    if len(episodes) <= 50:
        return episodes

    from relationship_engine import _call_claude_json

    old_batch = episodes[:5]
    remaining = episodes[5:]

    summaries = "\n".join(
        f"Episode {e.get('id', '?')} ({e.get('timestamp_start', '?')} ~ {e.get('timestamp_end', '?')}): "
        f"{e.get('summary', '')}"
        for e in old_batch
    )

    all_topics = []
    all_facts = []
    for e in old_batch:
        all_topics.extend(e.get('topics', []))
        all_facts.extend(e.get('key_facts_learned', []))

    prompt = f"""Merge these 5 episode summaries into ONE condensed episode.

Episodes:
{summaries}

All topics covered: {', '.join(set(all_topics))}
All facts learned: {json.dumps(list(set(all_facts)), ensure_ascii=False)}

Return JSON:
{{
  "summary": "3-4 sentence merged summary",
  "topics": ["merged topics (max 5)"],
  "key_facts_learned": ["merged facts (keep only important ones)"],
  "emotional_tone": "overall tone across all episodes"
}}

Return ONLY valid JSON."""

    system = "You are a summarizer. Merge episode summaries into one concise entry. Return ONLY valid JSON."

    try:
        result = await _call_claude_json(prompt, system, model=model)
    except Exception as e:
        logger.error(f"Episode recompression failed for {name}: {e}")
        return episodes  # Return unchanged on failure

    ts_start = old_batch[0].get('timestamp_start', '')
    ts_end = old_batch[-1].get('timestamp_end', '')

    merged = {
        'id': old_batch[0].get('id', 0),
        'timestamp_start': ts_start,
        'timestamp_end': ts_end,
        'summary': result.get('summary', ''),
        'topics': result.get('topics', []),
        'key_facts_learned': result.get('key_facts_learned', []),
        'emotional_tone': result.get('emotional_tone', ''),
        'unresolved': None,
        'merged_from': [e.get('id', 0) for e in old_batch],
    }

    new_episodes = [merged] + remaining
    logger.info(f"Recompressed episodes {old_batch[0].get('id')}-{old_batch[-1].get('id')} for {name}")
    return new_episodes


def format_episodes_for_prompt(name: str, max_tokens: int = 800) -> str:
    """Format recent episodes for injection into the response prompt.

    Args:
        name: Person identifier.
        max_tokens: Approximate token budget (chars / 4).

    Returns:
        Formatted string for prompt injection.
    """
    episodes = load_episodes(name)
    if not episodes:
        return "(No past episodes)"

    # Take most recent episodes, working backwards within budget
    lines = []
    char_budget = max_tokens * 4  # rough chars-to-tokens ratio
    used = 0

    for ep in reversed(episodes):
        summary = ep.get('summary', '')
        ts = ep.get('timestamp_start', '?')
        tone = ep.get('emotional_tone', '')
        unresolved = ep.get('unresolved')

        line = f"[{ts}] {summary}"
        if tone:
            line += f" (tone: {tone})"
        if unresolved:
            line += f" [UNRESOLVED: {unresolved}]"

        line_len = len(line)
        if used + line_len > char_budget:
            break
        lines.append(line)
        used += line_len

    lines.reverse()
    return "\n".join(lines) if lines else "(No past episodes)"
