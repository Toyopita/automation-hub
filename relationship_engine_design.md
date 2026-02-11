# Relationship Engine - Architecture Design Document

## 1. Overview

### Purpose
Transform the monolithic `aljela_auto_bot.py` (1200 lines) into a modular, horizontally-scalable relationship engine. The engine manages autonomous LINE conversations that naturally evolve from friendship to romantic relationship, while adapting to each person's unique communication style and emotional patterns.

### Design Principles
- **Config-driven**: Adding a new person = new config JSON + LINE/Discord tokens
- **Stateful learning**: Every conversation enriches a persistent profile
- **Budget-aware**: All decisions respect the 200 messages/month LINE constraint
- **Safety-first**: Automated de-escalation, never escalate when risk is elevated
- **Transparent**: All decisions logged to Discord with full reasoning

---

## 2. Architecture

### Component Diagram

```
                        +-----------------------+
                        |   LINE Webhook (FastAPI)|
                        |   /callback (per port)  |
                        +----------+------------+
                                   |
                                   v
+------------------------------------------------------------------+
|                      Message Router                               |
|  - Batch incoming messages (90s window)                          |
|  - Route to correct PersonContext by LINE user ID                |
+------------------------------------------------------------------+
           |                    |                    |
           v                    v                    v
  +------------------+  +------------------+  +------------------+
  |  PersonContext    |  |  PersonContext    |  |  PersonContext    |
  |  (Aljela)        |  |  (Person B)       |  |  (Person C)       |
  +--------+---------+  +--------+---------+  +--------+---------+
           |                    |                    |
           v                    v                    v
+------------------------------------------------------------------+
|                    Relationship Engine Core                       |
|                                                                  |
|  +------------------+  +-------------------+  +----------------+ |
|  | Profile Learner  |  | Strategy Engine   |  | Stage Manager  | |
|  | (analyze & store)|  | (decide actions)  |  | (track stages) | |
|  +------------------+  +-------------------+  +----------------+ |
|                                                                  |
|  +------------------+  +-------------------+  +----------------+ |
|  | Persona Adapter  |  | Timing Controller |  | Budget Manager | |
|  | (style matching) |  | (delay & silence) |  | (200/mo limit) | |
|  +------------------+  +-------------------+  +----------------+ |
+------------------------------------------------------------------+
           |                    |
           v                    v
  +------------------+  +------------------+
  | Claude CLI       |  | Discord Logger   |
  | (response gen)   |  | (monitoring)     |
  +------------------+  +------------------+
           |
           v
  +------------------+
  | LINE Push API    |
  +------------------+
```

### Data Flow (per incoming message batch)

```
1. LINE Webhook receives message(s)
2. Message Router batches (90s window) and routes to PersonContext
3. PersonContext triggers parallel:
   a. Profile Learner: Extract facts, preferences, patterns
   b. Emotion Analyzer: Score emotional state (6-axis for bot, 12-axis for manual)
   c. Stage Manager: Evaluate signals, check for stage transition
4. Strategy Engine evaluates:
   a. Should respond? (budget, timing, strategic silence)
   b. What stage-appropriate behavior? (topic, tone, depth)
   c. What topics to use? (rotation check, relevance to profile)
5. Persona Adapter builds prompt:
   a. Load learned communication preferences
   b. Inject relevant memories/facts
   c. Calibrate tone to emotion state
6. Claude CLI generates response
7. Timing Controller calculates delay
8. Budget Manager approves/denies send
9. LINE Push API sends
10. Discord Logger records everything
11. Profile Learner updates with outgoing message data
```

---

## 3. Component Details

### 3.1 Profile Learner

**Purpose**: Continuously build and refine a model of the person from every conversation exchange.

**Trigger**: After each message batch is processed (both incoming and outgoing).

**Learning Dimensions**:

| Dimension | What to Extract | How |
|-----------|----------------|-----|
| Topics of Interest | What she talks about most, what generates long responses | Track topic tags per message, measure response length/engagement |
| Communication Style | Emoji usage, message length, formality, response speed | Statistical tracking over time |
| Reaction Patterns | What topics excite her, what makes her go quiet | Correlate topic tags with emotion scores |
| Personality Traits | Introvert/Extrovert, Feeling/Thinking, etc. | Accumulate signals over time |
| Facts | Job, hobbies, family, schedule, preferences | Extract and store as structured data |
| NG Topics | Topics that cause negative reactions | Detect engagement drops or risk escalation |
| Temporal Patterns | When she's most active, response time by hour/day | Statistical tracking |
| Language Patterns | Vocabulary level, slang usage, grammar patterns | Frequency analysis |

**Implementation**: Post-conversation Claude CLI call with a specialized extraction prompt. Results merged into the person's profile JSON.

**Prompt Design (Profile Update)**:
```
Given the following conversation exchange, extract any new information
about {person_name}. Update the existing profile with new facts,
refined personality scores, and observed patterns.

Existing profile: {current_profile_json}
New conversation: {messages}

Return JSON with:
{
  "new_facts": [...],
  "updated_traits": {...},
  "topic_engagement": {...},
  "style_observations": {...}
}
```

### 3.2 Strategy Engine

**Purpose**: Decide *what* to do in response to incoming messages, based on relationship stage, emotional state, budget, and learned patterns.

**Decision Matrix by Stage**:

| Stage | Behavior | Topics | Tone | Frequency |
|-------|----------|--------|------|-----------|
| friends | Light, fun, build rapport | Daily life, hobbies, culture, work | Casual, warm, curious | Moderate (4-6/day) |
| close_friends | Deeper sharing, vulnerability | Personal stories, dreams, fears, inside jokes | Warm, caring, occasionally serious | Higher (5-8/day) |
| flirty | Playful tension, compliments | Appearance, attraction hints, teasing, "what if" | Playful, confident, slightly mysterious | Variable (3-7/day) |
| romantic | Direct interest, feelings | Feelings, future, physical attraction, exclusivity | Affectionate, honest, passionate | Adaptive (3-6/day) |

**Strategic Behaviors**:

```python
class StrategyDecision:
    should_respond: bool       # False = strategic silence
    delay_override: int | None # Override normal delay calculation
    topic_suggestion: str      # Suggested topic direction
    tone_directive: str        # Tone instruction for persona
    escalation_level: float    # 0.0 (pull back) to 1.0 (advance)
    end_conversation: bool     # Naturally end this exchange
```

**Push-Pull Balance Algorithm**:

```
Recent 10 messages analysis:
- Count YOUR initiations vs HER initiations
- Count YOUR questions vs HER questions
- Count YOUR emotional depth vs HER emotional depth

If ratio > 0.6 (you're pushing too much):
  -> Suggest pull-back behavior (shorter messages, less questions, strategic silence)

If ratio < 0.3 (you're too distant):
  -> Suggest push behavior (initiate, share, ask deeper questions)

Target ratio: 0.4-0.5 (slightly more pull than push)
```

**Topic Rotation**:

```python
class TopicTracker:
    # Track last N topics discussed
    recent_topics: deque[str]  # maxlen=20

    # Topic freshness score (0.0 = just discussed, 1.0 = fresh)
    def freshness(self, topic: str) -> float:
        if topic not in self.recent_topics:
            return 1.0
        position = list(self.recent_topics).index(topic)
        return position / len(self.recent_topics)

    # Suggest next topic based on freshness + profile interests
    def suggest_topic(self, profile: PersonProfile) -> str:
        candidates = profile.interested_topics
        scored = [(t, self.freshness(t) * profile.topic_engagement[t])
                  for t in candidates]
        return max(scored, key=lambda x: x[1])[0]
```

**Strategic Silence Rules**:
1. After she sends a conversation-ending message (bye, goodnight, etc.)
2. When Push-Pull ratio > 0.7 (too eager)
3. When daily budget is at 1 remaining (save for reactive only)
4. Random 10% chance on low-engagement messages (creates mystery)
5. After 3+ consecutive long responses from you (let her miss you)

**De-escalation Protocol**:
When emotion analysis shows `risk: caution` or `risk: danger`:
1. Reduce message length by 50%
2. Shift to supportive/empathetic tone
3. Avoid questions (give space)
4. Don't initiate for 24-48 hours after resolution
5. Log alert to Discord with `@mention` if danger level

### 3.3 Adaptive Persona

**Purpose**: Generate responses that match both the user's real communication style and adapt to what the specific person responds best to.

**Base Persona** (from config, shared across all persons):
```json
{
  "identity": {
    "age": "early 30s",
    "nationality": "Japanese",
    "occupation": "traditional/cultural organization",
    "side_passion": "music production",
    "personality": ["confident", "warm", "witty", "observant", "curious"]
  },
  "communication_defaults": {
    "message_length": "1-3 sentences usually",
    "emoji_frequency": "minimal",
    "humor_style": "natural, not forced",
    "question_frequency": "not every message"
  }
}
```

**Person-Adaptive Layer** (learned per person):
```json
{
  "style_adjustments": {
    "emoji_match": 0.7,        // Match 70% of her emoji frequency
    "length_match": 0.8,       // Match 80% of her message length
    "formality_match": 0.9,    // Match 90% of her formality level
    "humor_escalation": 1.2    // Slightly more humor than her
  },
  "effective_patterns": [
    {"pattern": "sharing_music", "engagement_boost": 2.3},
    {"pattern": "asking_about_food", "engagement_boost": 1.8},
    {"pattern": "light_teasing", "engagement_boost": 1.5}
  ],
  "avoid_patterns": [
    {"pattern": "too_many_questions", "engagement_drop": -1.2},
    {"pattern": "long_paragraphs", "engagement_drop": -0.8}
  ]
}
```

**Prompt Construction Pipeline**:

```
1. Base persona (identity, defaults)
2. + Stage-specific behavior instructions
3. + Learned style adjustments for this person
4. + Emotion-calibrated tone directive
5. + Topic suggestion from Strategy Engine
6. + Memory injection (relevant past facts/events)
7. + Budget awareness
8. + Conversation history (last 30 messages)
9. + Incoming message(s)
= Final prompt to Claude CLI
```

**Memory Injection**:
Before generating a response, search the person's profile for facts relevant to the current conversation. For example:
- If she mentions work -> inject her job details, past work complaints
- If she mentions food -> inject her favorite foods, dietary preferences
- If it's near a date she mentioned -> inject the event

### 3.4 Stage Manager

**Purpose**: Automatically track and transition relationship stages based on accumulated signals.

**Signal Detection**:

```python
POSITIVE_SIGNALS = {
    # Signal: weight
    "initiates_conversation": 2,
    "asks_personal_questions": 2,
    "shares_personal_info": 3,
    "uses_affectionate_language": 3,
    "sends_photos_selfies": 4,
    "mentions_meeting_up": 5,
    "compliments": 2,
    "long_engaged_responses": 1,
    "uses_emojis_hearts": 2,
    "responds_quickly": 1,
    "late_night_conversations": 2,
    "inside_jokes_references": 3,
    "expresses_missing_you": 4,
    "voice_messages": 3,
}

NEGATIVE_SIGNALS = {
    "short_one_word_responses": -2,
    "delayed_responses_consistently": -1,
    "avoids_personal_topics": -2,
    "conversation_ending_quickly": -2,
    "ignores_messages": -3,
    "formal_tone_increase": -2,
    "removes_emojis_affection": -2,
    "mentions_other_people_romantically": -4,
    "explicit_boundary_setting": -5,
    "blocks_or_restricts": -10,
}
```

**Stage Transition Thresholds**:

```
friends -> close_friends:
  - Minimum 14 days in stage
  - Positive score >= 30
  - No negative signals >= -5 in last 7 days
  - At least 3 instances of personal sharing
  - At least 1 instance of her initiating conversation

close_friends -> flirty:
  - Minimum 14 days in stage
  - Positive score >= 50
  - At least 2 compliment exchanges
  - Emotion analysis: intimacy average >= 5.0 in last 7 days
  - No risk: caution/danger in last 7 days

flirty -> romantic:
  - Minimum 21 days in stage
  - Positive score >= 80
  - Mutual expression of attraction
  - Emotion analysis: longing average >= 6.0 in last 7 days
  - At least 1 discussion about meeting up
```

**Anti-Rush Protections**:
1. Minimum days in each stage (cannot skip)
2. Maximum 1 stage transition per 2 weeks
3. Transition requires 3 consecutive days of above-threshold signals
4. Any `risk: danger` event resets the transition countdown
5. Stage demotion if negative signals accumulate (close_friends -> friends possible)

**Stage Demotion Rules**:
```
If negative_score in 7 days >= -15:
  -> Demote one stage
  -> Reset positive score to 50% of current
  -> Log to Discord with alert
  -> Activate de-escalation protocol for 48 hours
```

### 3.5 Timing Controller

**Purpose**: Make response timing feel human and natural.

**Enhanced from current implementation with person-specific learning**:

```python
class TimingController:
    def calculate_delay(self, context: MessageContext) -> int:
        """Returns delay in seconds, or -1 for do-not-respond"""

        # 1. Base: time-of-day (existing logic)
        base = self._time_of_day_base()

        # 2. Conversation momentum
        momentum = self._momentum_factor(context)

        # 3. Her response time matching
        # If she takes 20 min to reply, we should take ~15-25 min
        her_avg = context.profile.avg_response_time_minutes
        match_factor = self._response_time_match(her_avg, base)

        # 4. Stage adjustment (closer relationship = faster responses)
        stage_factor = {
            "friends": 1.2,
            "close_friends": 1.0,
            "flirty": 0.8,
            "romantic": 0.7
        }[context.stage]

        # 5. Emotion-based adjustment
        if context.emotion.engagement >= 8:
            emotion_factor = 0.5  # She's very engaged, respond faster
        elif context.emotion.risk in ("caution", "danger"):
            emotion_factor = 1.5  # Give space
        else:
            emotion_factor = 1.0

        # 6. Random jitter (+-30%)
        jitter = random.uniform(0.7, 1.3)

        delay = base * momentum * match_factor * stage_factor * emotion_factor * jitter
        return max(60, min(7200, int(delay)))  # 1min - 2hours
```

**Proactive Message Initiation**:

```python
class ProactiveScheduler:
    """Initiate conversation when she hasn't messaged"""

    async def check_and_initiate(self, person: PersonContext):
        hours_since_last = person.hours_since_last_exchange()

        # Don't initiate too early
        if hours_since_last < 8:
            return

        # Don't initiate if she's likely sleeping
        if person.is_likely_sleeping():
            return

        # Budget check
        if not person.budget.can_send():
            return

        # Push-Pull check (don't initiate if we initiated last 2 times)
        if person.last_n_initiators(2) == ["you", "you"]:
            return

        # Stage-specific initiation frequency
        initiation_windows = {
            "friends": (24, 72),      # Initiate after 24-72 hours
            "close_friends": (16, 48), # More frequent
            "flirty": (12, 36),
            "romantic": (8, 24),
        }
        min_h, max_h = initiation_windows[person.stage]

        if hours_since_last >= min_h:
            # Probability increases with time
            prob = min(0.8, (hours_since_last - min_h) / (max_h - min_h))
            if random.random() < prob:
                await self.generate_initiation(person)

    async def generate_initiation(self, person: PersonContext):
        """Generate a natural conversation starter"""
        # Use profile to pick a relevant topic
        topic = person.strategy.suggest_initiation_topic()
        # Generate via Claude with initiation-specific prompt
        # Send via LINE
```

### 3.6 Budget Manager

**Enhanced from current implementation. No structural changes needed -- current `MessageBudget` class is well-designed.**

**Additions**:
- Per-person budget split when multiple persons are active
- Priority weighting (person with higher engagement gets more budget)

```python
class MultiPersonBudget:
    def allocate(self, persons: list[PersonContext]) -> dict[str, int]:
        """Allocate daily budget across persons"""
        total_daily = self.calculate_daily_budget()

        if len(persons) == 1:
            return {persons[0].name: total_daily}

        # Weight by engagement and stage
        weights = {}
        for p in persons:
            stage_weight = {"friends": 1.0, "close_friends": 1.5,
                          "flirty": 2.0, "romantic": 2.5}[p.stage]
            engagement = p.recent_engagement_score()  # 0-10
            weights[p.name] = stage_weight * (engagement / 5.0)

        total_weight = sum(weights.values())
        allocation = {
            name: max(1, round(total_daily * w / total_weight))
            for name, w in weights.items()
        }
        return allocation
```

---

## 4. Data Structures

### 4.1 Person Config (`{name}_config.json`)

```json
{
  "name": "aljela",
  "display_name": "Aljela",
  "languages": "English",
  "background": "Woman in her 20s, lives in Southeast Asia. Friend.",
  "relationship_tone": "casual and friendly",

  "timezone": "Asia/Manila",
  "timezone_label": "PHT",

  "port": 8788,

  "env": {
    "line_channel_secret": "LINE_ALJELA_CHANNEL_SECRET",
    "line_access_token": "LINE_ALJELA_ACCESS_TOKEN",
    "discord_token": "DISCORD_TOKEN_ALJELA",
    "discord_channel_id": "ALJELA_DISCORD_CHANNEL_ID"
  },

  "emotion_analysis": true,
  "claude_model": "claude-sonnet-4-5-20250929",

  "stage_overrides": {
    "min_days_per_stage": 14,
    "enable_flirty": true,
    "enable_romantic": true
  },

  "proactive_messaging": {
    "enabled": true,
    "min_hours_silence": 24,
    "max_hours_silence": 72
  }
}
```

### 4.2 Person Profile (`{name}_profile.json`)

```json
{
  "version": 2,
  "name": "Aljela",
  "last_updated": "2026-02-11T15:30:00+09:00",

  "facts": {
    "age": null,
    "location": "Southeast Asia (likely Philippines)",
    "occupation": null,
    "hobbies": [],
    "family": [],
    "languages": ["English"],
    "favorites": {
      "food": [],
      "music": [],
      "movies": [],
      "activities": []
    },
    "schedule": {
      "typical_active_hours": [],
      "work_schedule": null,
      "timezone_confirmed": false
    },
    "important_dates": [],
    "misc_facts": []
  },

  "personality": {
    "introversion": 5,
    "emotional_expressiveness": 5,
    "humor_appreciation": 5,
    "adventurousness": 5,
    "confidence": 5,
    "warmth": 5,
    "observations": []
  },

  "communication_style": {
    "avg_message_length": null,
    "emoji_frequency": "unknown",
    "preferred_emojis": [],
    "formality_level": "unknown",
    "response_time_avg_minutes": null,
    "active_hours": [],
    "conversation_starters_used": [],
    "vocabulary_level": "unknown",
    "grammar_patterns": []
  },

  "topic_engagement": {},

  "effective_patterns": [],
  "avoid_patterns": [],

  "ng_topics": [],

  "temporal_patterns": {
    "most_active_day": null,
    "most_active_hour": null,
    "avg_conversation_length_messages": null,
    "initiates_ratio": null
  }
}
```

### 4.3 Relationship State (`{name}_relationship.json`)

```json
{
  "version": 2,
  "stage": "friends",
  "stage_history": [
    {
      "stage": "friends",
      "entered": "2026-02-11",
      "exited": null
    }
  ],
  "started": "2026-02-11",

  "signals": {
    "positive": {
      "total_score": 0,
      "recent_7d": [],
      "history": []
    },
    "negative": {
      "total_score": 0,
      "recent_7d": [],
      "history": []
    }
  },

  "transition_readiness": {
    "days_in_stage": 0,
    "consecutive_positive_days": 0,
    "last_risk_event": null,
    "blocked_until": null
  },

  "push_pull": {
    "recent_initiators": [],
    "your_question_count": 0,
    "her_question_count": 0,
    "balance_score": 0.5
  },

  "topic_history": [],

  "total_exchanges": 0,
  "total_days_active": 0,
  "notes": []
}
```

### 4.4 Emotion History (`{name}_emotion_data.json`)

Same v2 format as current `aljela_emotion_data.json` -- no changes needed. Already well-structured with scores, deltas, timestamps.

### 4.5 Conversation Buffer (`{name}_conversation_buffer.json`)

Enhanced with metadata:

```json
[
  {
    "role": "aljela",
    "text": "Hey! How was your day?",
    "time": "2026-02-11 15:30",
    "topic_tags": ["greeting", "daily"],
    "emotion_snapshot": {"engagement": 7, "mood": 7}
  },
  {
    "role": "you",
    "text": "Pretty good! Just finished some work on music.",
    "time": "2026-02-11 15:45",
    "topic_tags": ["daily", "music"],
    "strategy_used": "share_personal",
    "delay_seconds": 900
  }
]
```

---

## 5. Prompt Design

### 5.1 Response Generation Prompt (Enhanced)

```
You are impersonating a real person in a LINE chat conversation with {display_name}.

=== WHO YOU ARE ===
{base_persona_from_config}

=== WHO IS {display_name} ===
{learned_profile_summary}

=== RELATIONSHIP STAGE: {stage} ===
{stage_specific_instructions}

=== STRATEGY DIRECTIVE ===
{strategy_engine_output}
- Suggested topic direction: {topic_suggestion}
- Tone: {tone_directive}
- Escalation level: {escalation_level}
- Push-Pull balance: {push_pull_status}

=== THINGS YOU REMEMBER ABOUT HER ===
{relevant_facts_from_profile}

=== HER COMMUNICATION PREFERENCES (learned) ===
{communication_style_summary}

=== EFFECTIVE PATTERNS (do more of these) ===
{effective_patterns}

=== AVOID PATTERNS (do less of these) ===
{avoid_patterns}

=== EMOTIONAL STATE ===
{emotion_analysis_results}

=== BUDGET ===
Daily remaining: {daily_remaining}
Monthly remaining: {monthly_remaining}

=== CONVERSATION HISTORY (last 30 messages) ===
{conversation_history}

=== INCOMING MESSAGE(S) ===
{messages}

=== INSTRUCTIONS ===
Return ONLY valid JSON:
{
  "should_respond": true/false,
  "message": "your response",
  "reasoning": "brief reasoning (Japanese OK)",
  "topic_tags": ["topics covered"],
  "signals_detected": ["positive or negative signals from her message"],
  "push_pull_action": "push/pull/neutral"
}
```

### 5.2 Profile Learning Prompt

```
Analyze this conversation exchange and extract learnings about {display_name}.

Current known profile:
{current_profile_json}

Recent conversation:
{messages}

Extract and return JSON:
{
  "new_facts": [
    {"category": "hobby", "fact": "likes cooking", "confidence": 0.8, "source_quote": "I made pasta today"}
  ],
  "personality_updates": {
    "warmth": {"value": 7, "evidence": "uses lots of affectionate language"}
  },
  "communication_observations": {
    "emoji_frequency": "moderate (2-3 per message)",
    "avg_length": "1-2 sentences",
    "new_vocabulary": ["ngl", "lowkey"]
  },
  "topic_engagement": {
    "food": 8,
    "music": 6,
    "work": 3
  },
  "signals": [
    {"type": "positive", "signal": "asks_personal_questions", "evidence": "asked about your family"}
  ]
}
```

### 5.3 Proactive Initiation Prompt

```
You are impersonating a real person. You want to start a conversation with {display_name}.

Context:
- Last conversation was {hours_ago} hours ago
- Last topic discussed: {last_topic}
- Current time for her: {her_local_time}
- Things she's interested in: {interests}
- Recent events she mentioned: {recent_events}
- Current stage: {stage}

Generate a natural, casual conversation starter.
Do NOT:
- Be too eager or clingy
- Reference the time gap ("haven't talked in a while")
- Ask generic questions ("how are you")

DO:
- Reference something specific (her interests, recent event, shared joke)
- Keep it light and natural
- Match the current relationship stage

Return JSON:
{
  "message": "your opener",
  "topic": "topic category",
  "reasoning": "why this opener works"
}
```

---

## 6. File Structure

```
~/discord-mcp-server/
  |
  |-- relationship_engine.py          # Core engine (shared module)
  |     - ProfileLearner class
  |     - StrategyEngine class
  |     - StageManager class
  |     - PersonaAdapter class
  |     - TimingController class
  |     - ProactiveScheduler class
  |     - MultiPersonBudget class
  |
  |-- aljela_auto_bot.py              # Existing bot (refactored to use engine)
  |     - FastAPI webhook handler
  |     - Discord logging
  |     - LINE API calls
  |     - Main loop
  |     - References relationship_engine.py
  |
  |-- aljela_config.json              # Existing config
  |-- aljela_relationship.json        # Enhanced with v2 schema
  |-- aljela_profile.json             # NEW: learned profile data
  |-- aljela_emotion_data.json        # Existing emotion data
  |-- .aljela_conversation_buffer.json # Existing conversation buffer
  |-- aljela_budget.json              # Existing budget data
  |
  |-- relationship_engine_design.md   # This document
  |
  |-- start_line_bot_tmux.sh          # Existing launcher
```

### Adding a New Person

1. Create `{name}_config.json` (copy from template, edit fields)
2. Set environment variables in `.env`:
   - `LINE_{NAME}_CHANNEL_SECRET`
   - `LINE_{NAME}_ACCESS_TOKEN`
   - `DISCORD_TOKEN_{NAME}`
   - `{NAME}_DISCORD_CHANNEL_ID`
3. Create launchd plist (copy from aljela template, change port and config path)
4. The engine auto-creates `{name}_profile.json`, `{name}_relationship.json`, etc. on first run

No code changes required. The engine reads config and creates all state files automatically.

---

## 7. Implementation Priority

### Phase 1: Foundation (Week 1)
**Goal**: Extract shared logic into `relationship_engine.py` without breaking existing functionality.

1. **Create `relationship_engine.py`** with:
   - `PersonContext` class (holds all state for one person)
   - `ProfileLearner` class (basic fact extraction)
   - `StageManager` class (signal tracking, stage transitions)
   - Config-driven initialization

2. **Refactor `aljela_auto_bot.py`** to:
   - Import from `relationship_engine.py`
   - Load config from JSON
   - Use `PersonContext` for state management
   - Keep all existing LINE/Discord/webhook code in the bot file

3. **Migrate data files** to v2 schema (backward compatible)

### Phase 2: Intelligence (Week 2)
**Goal**: Add learning and strategy capabilities.

4. **Profile Learner**: Post-conversation fact extraction via Claude
5. **Strategy Engine**: Push-Pull tracking, topic rotation, strategic silence
6. **Enhanced Prompt**: Inject profile data and strategy directives into response generation

### Phase 3: Proactive (Week 3)
**Goal**: Bot initiates conversations naturally.

7. **Proactive Scheduler**: Monitor silence duration, generate conversation starters
8. **Timing Controller Enhancement**: Response time matching, momentum detection
9. **Multi-Person Budget**: Allocate budget across persons

### Phase 4: Refinement (Week 4+)
**Goal**: Continuous improvement through data.

10. **Pattern Analysis**: Which messages/topics produce best engagement?
11. **Stage Transition Tuning**: Adjust thresholds based on real data
12. **Dashboard Enhancement**: Visualize profile, strategy decisions, stage progress

---

## 8. Key Design Decisions

### Why Claude CLI (not API)?
- Avoids storing API keys in the bot
- Uses existing Claude CLI authentication
- `/tmp` execution avoids CLAUDE.md interference
- Cost management through Sonnet model selection

### Why not one monolithic bot for all persons?
- Different LINE accounts require different webhook endpoints (different ports)
- Each person has independent Discord monitoring channels
- Crash isolation: one bot crashing doesn't affect others
- But they share `relationship_engine.py` for logic

### Why separate Profile from Relationship state?
- Profile = facts about the person (relatively static, grows over time)
- Relationship = dynamic state (stage, signals, push-pull balance)
- Different update frequencies and purposes
- Profile survives a relationship reset; relationship state can be cleared

### Why conservative stage transitions?
- False positives in relationship escalation are costly (can scare someone away)
- Better to be slightly too slow than too fast
- Minimum time requirements prevent misreading a single good conversation as a stage change
- Human can always manually override via Discord commands

### Budget Priority
- With 200 messages/month across potentially multiple persons, budget is the scarcest resource
- Every message must count: no throwaway responses
- Budget-awareness is injected at every decision point
- Emergency reserve (15 messages) ensures month-end coverage

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Bot says something inappropriate | Emotion-aware prompts, de-escalation protocol, Discord approval mode |
| Stage advances too fast | Minimum days per stage, consecutive positive requirement, anti-rush checks |
| She detects it's a bot | Keep messages short/natural, match her response times, strategic silence, never be "too perfect" |
| Budget exhaustion | Daily budget algorithm with jitter, momentum adjustment, reserve system |
| Data corruption | JSON write with atomic rename (write to .tmp, then rename), periodic backups |
| Claude CLI failure | 3-retry with exponential backoff, graceful fallback (log error, don't respond) |
| Negative spiral | Auto de-escalation, stage demotion, Discord alerts at risk:caution/danger |

---

Last updated: 2026-02-11
