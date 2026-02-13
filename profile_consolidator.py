#!/usr/bin/env python3
"""
Profile Consolidator - Periodic profile quality maintenance.

Consolidates misc_facts (dedup, merge similar), trims topic_engagement
and effective_patterns to prevent unbounded growth.

Usage:
  python3 profile_consolidator.py --name laura
  python3 profile_consolidator.py --name vita --dry-run
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger('profile_consolidator')

BASE_DIR = Path(__file__).parent
JST = ZoneInfo('Asia/Tokyo')

# Limits
MAX_MISC_FACTS = 60
MAX_TOPIC_ENGAGEMENT = 80
MAX_EFFECTIVE_PATTERNS = 15
MAX_AVOID_PATTERNS = 15


def should_consolidate(name: str) -> bool:
    """Check if consolidation is needed based on exchange count."""
    from relationship_engine import ProfileLearner
    learner = ProfileLearner()
    profile = learner.load_profile(name)

    count = profile.get('_exchange_count_since_consolidation', 0)
    return count >= 20


async def consolidate_profile(name: str, model: str = 'claude-sonnet-4-5-20250929',
                               dry_run: bool = False) -> dict:
    """Run full profile consolidation.

    Args:
        name: Person identifier.
        model: Claude model for fact merging.
        dry_run: If True, don't save changes.

    Returns:
        Dict with consolidation stats.
    """
    from relationship_engine import ProfileLearner, _call_claude_json

    learner = ProfileLearner()
    profile = learner.load_profile(name)
    stats = {'name': name}

    # --- 1. Consolidate misc_facts ---
    facts = profile.get('facts', {})
    misc_facts = facts.get('misc_facts', [])
    original_count = len(misc_facts)
    stats['misc_facts_before'] = original_count

    if original_count > MAX_MISC_FACTS:
        # Use Claude to merge/deduplicate
        misc_facts = await _consolidate_misc_facts(misc_facts, name, model)
        facts['misc_facts'] = misc_facts
        profile['facts'] = facts

    stats['misc_facts_after'] = len(facts.get('misc_facts', []))

    # --- 2. Trim topic_engagement to top 80 ---
    engagement = profile.get('topic_engagement', {})
    stats['topics_before'] = len(engagement)
    if len(engagement) > MAX_TOPIC_ENGAGEMENT:
        sorted_topics = sorted(
            engagement.items(),
            key=lambda x: (x[1].get('interest', x[1]) if isinstance(x[1], dict) else x[1]) or 0,
            reverse=True
        )
        profile['topic_engagement'] = dict(sorted_topics[:MAX_TOPIC_ENGAGEMENT])
    stats['topics_after'] = len(profile.get('topic_engagement', {}))

    # --- 3. Trim effective_patterns to top 15 ---
    eff = profile.get('effective_patterns', [])
    stats['effective_before'] = len(eff)
    if len(eff) > MAX_EFFECTIVE_PATTERNS:
        eff.sort(
            key=lambda x: abs(x.get('engagement_boost', 0)) if isinstance(x, dict) else 0,
            reverse=True
        )
        profile['effective_patterns'] = eff[:MAX_EFFECTIVE_PATTERNS]
    stats['effective_after'] = len(profile.get('effective_patterns', []))

    # --- 4. Trim avoid_patterns to top 15 ---
    avoid = profile.get('avoid_patterns', [])
    stats['avoid_before'] = len(avoid)
    if len(avoid) > MAX_AVOID_PATTERNS:
        avoid.sort(
            key=lambda x: abs(x.get('engagement_drop', 0)) if isinstance(x, dict) else 0,
            reverse=True
        )
        profile['avoid_patterns'] = avoid[:MAX_AVOID_PATTERNS]
    stats['avoid_after'] = len(profile.get('avoid_patterns', []))

    # --- 5. Reset exchange counter ---
    profile['_exchange_count_since_consolidation'] = 0
    profile['_last_consolidation'] = datetime.now(JST).isoformat()

    if not dry_run:
        profile['last_updated'] = datetime.now(JST).isoformat()
        learner.save_profile(name, profile)
        logger.info(f"Profile consolidated for {name}: "
                    f"misc_facts {stats['misc_facts_before']}->{stats['misc_facts_after']}, "
                    f"topics {stats['topics_before']}->{stats['topics_after']}")
    else:
        logger.info(f"[DRY RUN] Would consolidate {name}: {json.dumps(stats, indent=2)}")

    return stats


async def _consolidate_misc_facts(misc_facts: list, name: str,
                                    model: str) -> list:
    """Use Claude to merge similar facts and remove temporary observations."""
    from relationship_engine import _call_claude_json

    # Build facts text for Claude
    facts_text_parts = []
    for i, f in enumerate(misc_facts):
        if isinstance(f, dict):
            text = f.get('text', '')
            tags = f.get('tags', [])
            facts_text_parts.append(f"{i+1}. {text} [tags: {', '.join(tags)}]")
        elif isinstance(f, str):
            facts_text_parts.append(f"{i+1}. {f}")

    facts_text = "\n".join(facts_text_parts)

    prompt = f"""You are consolidating a profile's misc_facts list. Current count: {len(misc_facts)}, target: max {MAX_MISC_FACTS}.

Facts about {name}:
{facts_text}

Tasks:
1. MERGE similar/duplicate facts into single comprehensive facts
2. REMOVE temporary observations (e.g. "was tired today", "had a headache") unless they reveal a pattern
3. KEEP all important, unique, long-term facts
4. For each kept/merged fact, provide updated tags (5-10 tags each)

Return JSON:
{{
  "consolidated": [
    {{"text": "merged or kept fact text", "tags": ["tag1", "tag2", ...], "merged_from": [1, 3, 7]}}
  ]
}}

"merged_from" lists the original fact numbers that were merged. Single facts use their own number.
Target: {MAX_MISC_FACTS} facts or fewer.
Return ONLY valid JSON."""

    system = ("You are a data consolidation specialist. Merge duplicates, remove temporaries, "
              "keep important facts. Return ONLY valid JSON.")

    try:
        result = await _call_claude_json(prompt, system, model=model)
    except Exception as e:
        logger.error(f"Fact consolidation failed for {name}: {e}")
        # Fallback: just trim to limit
        return misc_facts[:MAX_MISC_FACTS]

    consolidated = result.get('consolidated', [])
    if not consolidated:
        return misc_facts[:MAX_MISC_FACTS]

    now = datetime.now(JST).strftime('%Y-%m-%d')
    new_facts = []
    for entry in consolidated:
        new_facts.append({
            'text': entry.get('text', ''),
            'tags': entry.get('tags', []),
            'added': now,
        })

    return new_facts[:MAX_MISC_FACTS]


def increment_exchange_count(name: str):
    """Increment the exchange counter for consolidation tracking."""
    from relationship_engine import ProfileLearner
    learner = ProfileLearner()
    profile = learner.load_profile(name)
    count = profile.get('_exchange_count_since_consolidation', 0) + 1
    profile['_exchange_count_since_consolidation'] = count
    learner.save_profile(name, profile)
    return count


# ============================================================
# CLI entry point
# ============================================================
async def main():
    parser = argparse.ArgumentParser(description='Profile Consolidator')
    parser.add_argument('--name', required=True, help='Person name (e.g. laura, vita)')
    parser.add_argument('--model', default='claude-sonnet-4-5-20250929', help='Claude model')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without saving')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

    stats = await consolidate_profile(args.name, model=args.model, dry_run=args.dry_run)
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
