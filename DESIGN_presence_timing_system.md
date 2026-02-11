# Realistic Conversation Timing Control System - Detailed Design

## Overview

This document describes 4 new classes to be added to `relationship_engine.py` and the
integration modifications to `auto_chat_bot.py`.  The goal is to make the bot's online /
offline behaviour indistinguishable from a real person who has a job, sleeps, eats, bathes,
and sometimes puts the phone down.

---

## Architecture Summary

```
                         ┌─────────────────────┐
                         │   PresenceManager    │  State: active / busy / away / sleeping
                         │  (new - RE L2060+)   │  Drives ALL timing decisions
                         └──────────┬──────────┘
                                    │ current state
              ┌─────────────────────┼─────────────────────┐
              v                     v                     v
   ┌───────────────────┐  ┌──────────────────┐  ┌────────────────────────┐
   │   GracefulExit    │  │ ScheduledReturn  │  │ PendingResponseHandler │
   │  (new - RE L2180+)│  │  (new - RE L2320+│  │  (new - RE L2450+)     │
   │                   │  │                  │  │                        │
   │ Generate natural  │  │ Schedule follow- │  │ Queue messages that    │
   │ "brb" messages    │  │ up after absence │  │ arrive during absence  │
   └───────────────────┘  └──────────────────┘  └────────────────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    v
                         ┌─────────────────────┐
                         │ StrategyEngine      │
                         │  .decide() modified │  Consults PresenceManager
                         └─────────┬───────────┘
                                   v
                         ┌─────────────────────┐
                         │  AutoChatBot        │
                         │  process_queued_    │  Modified flow
                         │  messages()         │
                         │  delayed_respond()  │
                         │  proactive_check    │
                         │  _loop()            │
                         └─────────────────────┘
```

---

## A. PresenceManager

### Purpose
Track the bot's simulated "presence" state.  Every timing decision (respond, wait,
sleep, initiate) consults this manager.

### Location
`relationship_engine.py`, after BotDetectionFilter (line ~2055).

### State Machine

```
                    ┌─────────────┐
          ┌────────>│   active     │<────────┐
          │         │ (online,     │         │
          │         │  can reply)  │         │
          │         └──────┬──────┘         │
          │                │                │
   auto 7:00-7:30    manual/timer      auto/manual
   (wake)              │                │
          │         ┌──────v──────┐    │
          │         │    busy      │    │
          │         │ (working,    │    │
          │         │  eating etc) │    │
          │         └──────┬──────┘    │
          │                │           │
          │            timer           │
          │                │           │
          │         ┌──────v──────┐    │
          │         │    away      │────┘
          │         │ (phone down, │
          │         │  shower etc) │
          │         └──────┬──────┘
          │                │
          │         auto 0:00-1:00
          │                │
          │         ┌──────v──────┐
          └─────────│  sleeping    │
                    │ (no reply   │
                    │  until ~7am)│
                    └─────────────┘
```

### Class Design

```python
@dataclass
class PresenceState:
    """Serialisable snapshot of presence."""
    status: str            # 'active' | 'busy' | 'away' | 'sleeping'
    since: str             # ISO timestamp (JST)
    reason: str            # e.g. 'work', 'eating', 'shower', 'sleeping', ''
    return_at: str | None  # ISO timestamp when expected back (None = unknown)
    exit_message_sent: bool  # True if we already sent a "brb" message
    pending_followup: bool   # True if ScheduledReturn has a pending callback


class PresenceManager:
    """
    Track simulated online/offline presence per person.
    State is persisted to {name}_presence.json so it survives restarts.
    """

    # --- Automatic state transitions based on JST hour ---
    # These fire once per hour from the proactive_check_loop
    AUTO_TRANSITIONS = {
        # hour_range: (new_state, reason, return_minutes_range)
        (0, 1):   ('sleeping',  'fell asleep',         None),           # 0:00-0:59 -> sleep
        (7, 7):   ('active',    'woke up',             None),           # 7:00-7:59 -> wake
        (9, 9):   ('busy',      'work starting',       (180, 300)),     # 9:00 -> busy 3-5h
        (12, 12): ('active',    'lunch break',         None),           # 12:00 -> active (lunch)
        (13, 13): ('busy',      'back to work',        (180, 300)),     # 13:00 -> busy 3-5h
        (18, 18): ('active',    'finished work',       None),           # 18:00 -> active (evening)
        (22, 23): ('away',      'winding down',        (30, 90)),       # 22-23 -> away briefly
    }

    # Variation: add jitter +/- 30 min to all auto transitions
    # Weekends: skip work transitions (9, 13), stay active longer

    def __init__(self, name: str):
        self.name = name
        self.state_file = BASE_DIR / f'{name}_presence.json'
        self.state = self._load()

    # --- Persistence ---
    def _load(self) -> PresenceState: ...
        # Load from {name}_presence.json, or create default (active)

    def _save(self): ...
        # Atomic JSON write

    # --- State queries ---
    def current_status(self) -> str:
        """Return 'active', 'busy', 'away', or 'sleeping'."""
        return self.state.status

    def is_available(self) -> bool:
        """Can respond to messages right now?"""
        return self.state.status == 'active'

    def is_sleeping(self) -> bool:
        return self.state.status == 'sleeping'

    def minutes_until_available(self) -> int | None:
        """Estimated minutes until we become active again. None if unknown."""
        if self.state.return_at:
            ...calculate delta...
        return None

    def should_queue_response(self) -> bool:
        """True if incoming messages should be queued for later (busy/away/sleeping)."""
        return self.state.status in ('busy', 'away', 'sleeping')

    # --- State transitions ---
    def transition(self, new_status: str, reason: str = '',
                   return_minutes: int | None = None,
                   exit_message_sent: bool = False) -> PresenceState:
        """
        Change state. Records timestamp, calculates return_at.

        Args:
            new_status: 'active', 'busy', 'away', 'sleeping'
            reason: human-readable reason (used by GracefulExit)
            return_minutes: minutes until expected return (None=unknown)
            exit_message_sent: whether a goodbye message was sent

        Returns:
            Updated PresenceState.
        """
        now = datetime.now(JST)
        self.state = PresenceState(
            status=new_status,
            since=now.isoformat(),
            reason=reason,
            return_at=(now + timedelta(minutes=return_minutes)).isoformat()
                      if return_minutes else None,
            exit_message_sent=exit_message_sent,
            pending_followup=(return_minutes is not None),
        )
        self._save()
        return self.state

    def check_auto_transitions(self) -> tuple[str, str] | None:
        """
        Called once per hour by proactive_check_loop.
        Returns (new_status, reason) if a transition should fire, else None.

        Logic:
        1. Get current JST hour and weekday
        2. Check AUTO_TRANSITIONS table
        3. Skip work transitions on weekends (Sat/Sun)
        4. Add jitter: only fire with ~70% probability to avoid clock-like precision
        5. Don't re-transition if already in that state
        """
        now = datetime.now(JST)
        hour = now.hour
        is_weekend = now.weekday() >= 5

        for (h_start, h_end), (new_status, reason, return_range) in self.AUTO_TRANSITIONS.items():
            if h_start <= hour <= h_end:
                # Skip work transitions on weekends
                if is_weekend and reason in ('work starting', 'back to work'):
                    continue
                # Don't re-transition
                if self.state.status == new_status:
                    return None
                # Jitter: 30% chance to delay by 1 hour
                if random.random() < 0.3:
                    return None
                return_min = random.randint(*return_range) if return_range else None
                return (new_status, reason, return_min)
        return None

    def check_return_time(self) -> bool:
        """
        Check if return_at has passed and we should transition back to active.
        Called frequently (every check cycle).

        Returns:
            True if transition to active occurred.
        """
        if not self.state.return_at:
            return False
        now = datetime.now(JST)
        return_at = datetime.fromisoformat(self.state.return_at)
        if now >= return_at:
            self.transition('active', reason='returned')
            return True
        return False

    def record_manual_send(self):
        """
        Called after any manual message send (from Discord).
        If we're busy/away, we become active (a real person who sends a message is active).
        """
        if self.state.status in ('busy', 'away'):
            self.transition('active', reason='manual message sent')
```

### Persistence File: `{name}_presence.json`

```json
{
  "status": "busy",
  "since": "2026-02-11T09:15:00+09:00",
  "reason": "work starting",
  "return_at": "2026-02-11T12:30:00+09:00",
  "exit_message_sent": true,
  "pending_followup": true
}
```

---

## B. GracefulExit

### Purpose
When the bot decides to go "away" or "busy" during an active conversation,
generate a natural excuse message first.

### Location
`relationship_engine.py`, after PresenceManager (line ~2180).

### Class Design

```python
class GracefulExit:
    """
    Generate natural "I'm going away" messages based on time-of-day,
    reason, and relationship stage.
    """

    # Pre-defined templates by reason and time, to avoid Claude API calls
    # for something that should be fast and cheap.
    # Each template set has multiple variants to avoid repetition.

    TEMPLATES = {
        'work': {
            'casual': [
                "gotta head to work, talk later",
                "ahh work time.. ttyl",
                "heading to work now, msg you later",
                "ok i gotta go to work lol talk later",
                "alright work calls.. later!",
            ],
            'warm': [
                "i gotta go to work but ill message you later ok",
                "work time unfortunately.. ill text you after",
                "heading to work now but lets continue this later",
                "ahh i need to go work but ill hit you up after",
            ],
        },
        'eating': {
            'casual': [
                "gonna go eat, brb",
                "food time lol be back",
                "grabbing dinner, talk in a bit",
                "gonna eat real quick",
                "lunch break gonna go eat",
            ],
            'warm': [
                "gonna go grab some food, be back soon",
                "getting hungry lol gonna eat and ill message you after",
                "dinner time! ill text you in a bit",
            ],
        },
        'shower': {
            'casual': [
                "gonna go shower real quick",
                "brb shower",
                "gonna take a bath, back soon",
                "need to shower lol be right back",
            ],
            'warm': [
                "gonna go take a shower, ill message you when im done",
                "bath time lol ill be back in a bit",
            ],
        },
        'sleeping': {
            'casual': [
                "getting sleepy.. gonna head to bed",
                "its getting late, gonna sleep",
                "alright im gonna crash, night",
                "eyes getting heavy lol gn",
                "ok i need to sleep, night night",
            ],
            'warm': [
                "getting really sleepy.. gonna go to bed but talk tomorrow ok?",
                "i should sleep, good night! ill message you tomorrow",
                "its so late haha i need to sleep.. sweet dreams",
                "alright im gonna sleep now, night! talk tomorrow",
            ],
        },
        'generic_busy': {
            'casual': [
                "gotta do something real quick, brb",
                "sorry need to handle something, back soon",
                "one sec gotta do something",
            ],
            'warm': [
                "sorry i need to step away for a bit, ill message you soon",
                "gotta take care of something but ill be back",
            ],
        },
        'appointment': {
            'casual': [
                "oh i have a thing i gotta go to",
                "just remembered i have plans lol gotta go",
                "need to head out, talk later",
            ],
            'warm': [
                "i have plans i need to get to but lets talk later!",
                "gotta go out for a bit, ill text you when im back",
            ],
        },
    }

    # Followup promises (appended to some messages)
    FOLLOWUP_PROMISES = [
        "",  # sometimes no promise (more natural)
        "",
        "msg you later",
        "talk later",
        "text you after",
        "ill be back",
    ]

    # Track recently used templates to avoid repetition
    _recent_used: dict[str, list[str]] = {}

    @classmethod
    def generate_exit_message(cls, reason: str, stage: str,
                               person_name: str) -> str | None:
        """
        Generate a natural departure message.

        Args:
            reason: 'work', 'eating', 'shower', 'sleeping', 'generic_busy', 'appointment'
            stage: relationship stage ('friends', 'close_friends', 'flirty', 'romantic')
            person_name: for tracking recently used templates

        Returns:
            Exit message string, or None if no message needed.
        """
        # Select tone based on stage
        if stage in ('flirty', 'romantic'):
            tone = 'warm'
        else:
            tone = 'casual'

        templates = cls.TEMPLATES.get(reason, cls.TEMPLATES['generic_busy'])
        options = templates.get(tone, templates.get('casual', []))

        if not options:
            return None

        # Filter out recently used (last 3)
        recent = cls._recent_used.get(person_name, [])
        available = [t for t in options if t not in recent]
        if not available:
            available = options  # reset if all used

        chosen = random.choice(available)

        # Track usage
        recent.append(chosen)
        cls._recent_used[person_name] = recent[-3:]

        return chosen

    @classmethod
    def should_send_exit_message(cls, conversation_buffer: list[dict],
                                  minutes_since_last_exchange: float) -> bool:
        """
        Determine if we should send an exit message before going away.

        Returns True if:
        - There was active conversation in the last 30 minutes
        - The last message was from the other person (so we don't leave them hanging)
        - We haven't already sent an exit message recently
        """
        if not conversation_buffer:
            return False

        if minutes_since_last_exchange > 30:
            return False  # Conversation already went cold, no need to announce departure

        last_msg = conversation_buffer[-1]
        if last_msg.get('role') == 'you':
            # Our last message - check if it was less than 10 min ago
            # (if we just sent something, natural to say brb)
            return minutes_since_last_exchange < 10

        # Their last message - we should acknowledge before disappearing
        return True

    @classmethod
    def pick_reason_for_time(cls) -> str:
        """
        Pick a plausible reason for going away based on current JST time.

        Returns:
            A reason key matching TEMPLATES.
        """
        hour = datetime.now(JST).hour

        if 8 <= hour <= 9:
            return random.choice(['work', 'work', 'appointment'])
        elif 11 <= hour <= 12:
            return 'eating'
        elif 13 <= hour <= 14:
            return random.choice(['work', 'generic_busy'])
        elif 17 <= hour <= 18:
            return random.choice(['eating', 'generic_busy'])
        elif 19 <= hour <= 21:
            return random.choice(['shower', 'eating', 'appointment', 'generic_busy'])
        elif 22 <= hour or hour <= 1:
            return 'sleeping'
        else:
            return 'generic_busy'
```

---

## C. ScheduledReturn

### Purpose
After a period of absence, automatically "come back" and optionally send a
follow-up message. This creates the pattern of a real person who leaves,
does their thing, and comes back to chat.

### Location
`relationship_engine.py`, after GracefulExit (line ~2320).

### Class Design

```python
class ScheduledReturn:
    """
    Calculate return timing and generate follow-up messages after absence.
    """

    # Return time ranges by reason (minutes)
    RETURN_TIMES = {
        'work':          (180, 480),   # 3-8 hours
        'eating':        (20, 60),     # 20-60 min
        'shower':        (15, 40),     # 15-40 min
        'sleeping':      (360, 540),   # 6-9 hours (calculated from sleep time to 7am)
        'generic_busy':  (15, 90),     # 15-90 min
        'appointment':   (60, 180),    # 1-3 hours
    }

    # Follow-up message templates (sent upon return)
    RETURN_MESSAGES = {
        'work': {
            'casual': [
                "just got off work",
                "finally done with work lol",
                "work was so long today",
                "ok im free now, work done",
            ],
            'warm': [
                "just finished work! how was your day?",
                "finally off work, was thinking about what you said earlier",
                "done with work now, missed chatting with you lol",
            ],
        },
        'eating': {
            'casual': [
                "ok im back",
                "that was good lol",
                "back, the food was nice",
            ],
            'warm': [
                "im back! the food was so good",
                "ok done eating, im back",
            ],
        },
        'shower': {
            'casual': [
                "ok back",
                "back lol that was refreshing",
                "ok shower done",
            ],
            'warm': [
                "back! feel so much better now",
                "ok im back, showers are the best lol",
            ],
        },
        'sleeping': {
            'casual': [
                "morning",
                "good morning",
                "ohayo",
                "just woke up",
            ],
            'warm': [
                "good morning! how did you sleep?",
                "morning! just woke up, you up yet?",
                "ohayo~ slept really well",
            ],
        },
        'generic_busy': {
            'casual': [
                "ok im back",
                "back",
                "sorry about that, im back now",
            ],
            'warm': [
                "im back! sorry for disappearing",
                "ok back, what were we talking about?",
            ],
        },
        'appointment': {
            'casual': [
                "im back",
                "ok done with that",
                "just got back",
            ],
            'warm': [
                "just got back! what did i miss?",
                "ok im free now",
            ],
        },
    }

    @classmethod
    def calculate_return_delay(cls, reason: str) -> int:
        """
        Calculate how many seconds until the bot should "return".

        For 'sleeping': calculates time from now until ~7:00-7:30 JST next morning.
        For others: random within the defined range.

        Returns:
            Delay in seconds.
        """
        if reason == 'sleeping':
            now = datetime.now(JST)
            wake_hour = 7
            wake_minute = random.randint(0, 30)
            wake_time = now.replace(hour=wake_hour, minute=wake_minute, second=0, microsecond=0)
            if wake_time <= now:
                wake_time += timedelta(days=1)
            return int((wake_time - now).total_seconds())

        min_min, max_min = cls.RETURN_TIMES.get(reason, (15, 90))
        minutes = random.randint(min_min, max_min)
        # Add small jitter (0-5 min)
        minutes += random.randint(0, 5)
        return minutes * 60

    @classmethod
    def generate_return_message(cls, reason: str, stage: str,
                                 person_name: str,
                                 pending_messages: list[str] | None = None) -> str | None:
        """
        Generate a follow-up message after returning from absence.

        Args:
            reason: why we were away
            stage: relationship stage
            person_name: for context
            pending_messages: messages received while away (used to decide
                            whether to send a return message or go straight
                            to responding)

        Returns:
            Return message string, or None if we should just respond to pending
            messages without a separate return announcement.
        """
        # If there are pending messages, we often skip the return announcement
        # and go straight to replying (a real person would do this)
        if pending_messages and len(pending_messages) > 0:
            # 70% chance to skip announcement and just reply
            if random.random() < 0.7:
                return None
            # 30% chance: combine return message + acknowledgment
            # (handled by caller who prepends return msg to the reply)

        if stage in ('flirty', 'romantic'):
            tone = 'warm'
        else:
            tone = 'casual'

        templates = cls.RETURN_MESSAGES.get(reason, cls.RETURN_MESSAGES['generic_busy'])
        options = templates.get(tone, templates.get('casual', []))

        if not options:
            return None

        return random.choice(options)

    @classmethod
    def should_send_followup(cls, reason: str, conversation_buffer: list[dict],
                              hours_away: float) -> bool:
        """
        Determine if we should proactively send a follow-up after returning.

        Returns True if:
        - We were away for a meaningful duration (>15 min for non-sleep)
        - The conversation was active before we left
        - We haven't exceeded push-pull limits
        """
        if not conversation_buffer:
            return False

        # For sleep: always follow up in the morning
        if reason == 'sleeping':
            return True

        # For short absences: only if conversation was active
        if hours_away < 0.25:  # less than 15 min
            return False

        # Check if last messages were from the other person (they're waiting)
        recent = conversation_buffer[-3:]
        other_count = sum(1 for m in recent if m.get('role') != 'you')
        if other_count >= 2:
            return True  # She sent messages while we were away

        # 50% chance otherwise
        return random.random() < 0.5
```

---

## D. PendingResponseHandler

### Purpose
Manage messages that arrive while the bot is busy/away/sleeping.
Handle them realistically upon return -- not all at once, but naturally.

### Location
`relationship_engine.py`, after ScheduledReturn (line ~2450).

### Class Design

```python
@dataclass
class PendingMessage:
    """A message received while away."""
    text: str
    received_at: str      # ISO timestamp
    urgency: str          # 'low', 'normal', 'high'
    is_question: bool
    is_emotional: bool


class PendingResponseHandler:
    """
    Queue and manage messages received during absence periods.
    Decides how to handle them upon return.
    """

    # Urgency detection patterns
    URGENT_PATTERNS = [
        re.compile(r'\?', re.I),                           # questions
        re.compile(r'\b(miss|love|worry|scared|help)\b', re.I),  # emotional
        re.compile(r'\b(emergency|urgent|asap|now)\b', re.I),     # explicit urgency
        re.compile(r'(sad|cry|upset|angry|mad)', re.I),           # emotional state
    ]

    EMOTIONAL_PATTERNS = [
        re.compile(r'(love|miss|think.*about|dream.*about)', re.I),
        re.compile(r'(sad|cry|upset|lonely|depressed)', re.I),
        re.compile(r'(heart|feel|emotion|hug)', re.I),
        re.compile(r'[😢😭💔🥺😔❤️💕💗🥰😍]'),
    ]

    def __init__(self, name: str):
        self.name = name
        self.queue_file = BASE_DIR / f'{name}_pending_queue.json'
        self.queue: list[PendingMessage] = self._load()

    def _load(self) -> list[PendingMessage]: ...
    def _save(self): ...

    def enqueue(self, text: str):
        """
        Add a message to the pending queue with urgency classification.
        Called when PresenceManager.should_queue_response() is True.
        """
        is_question = bool(re.search(r'\?', text))
        is_emotional = any(p.search(text) for p in self.EMOTIONAL_PATTERNS)
        urgency = self._classify_urgency(text, is_question, is_emotional)

        msg = PendingMessage(
            text=text,
            received_at=datetime.now(JST).isoformat(),
            urgency=urgency,
            is_question=is_question,
            is_emotional=is_emotional,
        )
        self.queue.append(msg)
        self._save()

    def _classify_urgency(self, text: str, is_question: bool,
                           is_emotional: bool) -> str:
        """
        Classify message urgency.

        - 'high': emotional distress, explicit urgency, multiple questions
        - 'normal': regular questions, engaged messages
        - 'low': statements, casual remarks, stickers
        """
        # Check explicit urgency
        if any(re.search(r'\b(emergency|urgent|asap|help)\b', text, re.I) for _ in [1]):
            return 'high'
        if is_emotional:
            return 'high'
        if is_question:
            return 'normal'
        if len(text) < 5:
            return 'low'
        return 'normal'

    def has_pending(self) -> bool:
        return len(self.queue) > 0

    def has_urgent(self) -> bool:
        return any(m.urgency == 'high' for m in self.queue)

    def get_all_texts(self) -> list[str]:
        """Return all pending message texts (for batch processing)."""
        return [m.text for m in self.queue]

    def get_pending_summary(self) -> dict:
        """
        Summary for decision making.

        Returns:
            {
                'count': int,
                'has_urgent': bool,
                'has_questions': bool,
                'oldest_minutes': float,  # how long the oldest message has been waiting
                'texts': list[str],
            }
        """
        if not self.queue:
            return {'count': 0, 'has_urgent': False, 'has_questions': False,
                    'oldest_minutes': 0, 'texts': []}

        now = datetime.now(JST)
        oldest = datetime.fromisoformat(self.queue[0].received_at)
        oldest_minutes = (now - oldest).total_seconds() / 60

        return {
            'count': len(self.queue),
            'has_urgent': self.has_urgent(),
            'has_questions': any(m.is_question for m in self.queue),
            'oldest_minutes': oldest_minutes,
            'texts': self.get_all_texts(),
        }

    def clear(self):
        """Clear the queue after messages have been processed."""
        self.queue = []
        self._save()

    def should_wake_early(self, current_state: str) -> bool:
        """
        Determine if urgent pending messages justify coming back early.

        Returns True if:
        - State is 'busy' or 'away' (not sleeping -- sleep is sacrosanct)
        - There are 'high' urgency messages
        - At least 5 minutes have passed (don't respond instantly even to urgent)
        """
        if current_state == 'sleeping':
            return False

        if not self.has_urgent():
            return False

        # Check if at least 5 min have passed since the first urgent message
        urgent_msgs = [m for m in self.queue if m.urgency == 'high']
        if not urgent_msgs:
            return False

        now = datetime.now(JST)
        first_urgent = datetime.fromisoformat(urgent_msgs[0].received_at)
        minutes_waiting = (now - first_urgent).total_seconds() / 60

        return minutes_waiting >= 5
```

### Persistence File: `{name}_pending_queue.json`

```json
[
  {
    "text": "hey are you there?",
    "received_at": "2026-02-11T10:30:00+09:00",
    "urgency": "normal",
    "is_question": true,
    "is_emotional": false
  }
]
```

---

## E. Integration with Existing Systems

### E1. Modifications to `StrategyEngine.decide()` (relationship_engine.py)

**Current**: `decide()` at line 575 takes stage, profile, emotion, budget, conversation_history
and returns `StrategyDecision`.

**Change**: Add `presence: PresenceState | None = None` parameter.

```python
# relationship_engine.py, StrategyEngine.decide() - line 575
def decide(self, stage: str, profile: dict, emotion: dict,
           budget: dict, conversation_history: list[dict],
           presence: PresenceState | None = None) -> StrategyDecision:
    """Produce a strategy decision."""
    decision = StrategyDecision()

    # NEW: Presence-based override (check first)
    if presence and presence.status != 'active':
        decision.should_respond = False
        decision.tone_directive = f"presence:{presence.status} ({presence.reason})"
        return decision

    # ... rest of existing logic unchanged ...
```

**StrategyDecision dataclass** - add new field:

```python
# line 487
@dataclass
class StrategyDecision:
    should_respond: bool = True
    delay_override: int | None = None
    topic_suggestion: str = ''
    tone_directive: str = ''
    escalation_level: float = 0.5
    end_conversation: bool = False
    presence_action: str = ''  # NEW: 'exit_graceful', 'queue_for_later', '', etc.
```

### E2. Modifications to `auto_chat_bot.py`

#### E2.1 AutoChatBot.__init__() - line 113

Add new component initialization:

```python
# After line 145 (self.proactive_scheduler = ProactiveScheduler())
self.presence_manager = PresenceManager(self.name)
self.pending_handler = PendingResponseHandler(self.name)
```

#### E2.2 process_queued_messages() - line 555

**Current flow:**
1. Bot detection
2. Emotion analysis
3. Profile + relationship load
4. Strategy decision
5. Translation
6. Discord log
7. Auto-respond check
8. Sleep time check
9. Strategic silence check
10. Budget check
11. Delay calculation
12. Create delayed_respond task

**New flow:**
1. **[NEW] Check presence state**
2. Bot detection
3. Emotion analysis
4. Profile + relationship load
5. Strategy decision **[MODIFIED: pass presence]**
6. Translation
7. Discord log
8. Auto-respond check
9. **[MODIFIED] Presence-based routing replaces simple sleep check**
10. Strategic silence check
11. Budget check
12. Delay calculation
13. Create delayed_respond task

```python
async def process_queued_messages(self):
    if not self.pending_messages:
        return

    messages = self.pending_messages.copy()
    self.pending_messages.clear()

    # ===== NEW: Presence check (before anything else) =====
    presence = self.presence_manager.state
    if self.presence_manager.should_queue_response():
        # Queue messages for later processing
        for msg in messages:
            self.pending_handler.enqueue(msg)
        self.logger.info(f"Queued {len(messages)} messages (presence: {presence.status})")

        # Check if urgent enough to wake early
        if self.pending_handler.should_wake_early(presence.status):
            self.logger.info("Urgent message detected, scheduling early return")
            # Transition to active after a short delay (5-15 min)
            early_delay = random.randint(5, 15) * 60
            asyncio.create_task(self._early_return(early_delay))

        # Still do emotion analysis and Discord logging
        # (but skip response generation)
        emotion_result = None
        try:
            emotion_result = await self.analyze_emotion(messages)
            self.log_emotion_data(messages, emotion_result)
        except Exception:
            pass

        translation = ""
        try:
            translation = await self.translate_to_japanese(messages)
        except Exception:
            pass

        await self.log_incoming(messages, emotion_data=emotion_result,
                               translation=translation)
        await self.log_to_discord(
            f"Queued ({presence.status})",
            f"{len(messages)} message(s) queued. Reason: {presence.reason}",
            color=0x9b59b6,
        )
        return
    # ===== END NEW =====

    # 0. Bot detection (unchanged)
    detection_result = BotDetectionFilter.analyze_batch(messages)
    # ... rest continues as before ...

    # MODIFIED: Pass presence to strategy decision (line ~601)
    strategy_decision = self.strategy_engine.decide(
        stage=stage,
        profile=profile,
        emotion=emotion,
        budget=budget_info,
        conversation_history=list(self.conversation_buffer),
        presence=self.presence_manager.state,  # NEW
    )

    # MODIFIED: Replace _is_sleep_time() check (line ~629) with presence check
    # REMOVE the old sleep time block:
    #   if self._is_sleep_time():
    #       ...
    # This is now handled by PresenceManager auto-transitions
```

#### E2.3 New method: _early_return() in AutoChatBot

```python
async def _early_return(self, delay_seconds: int):
    """Return early from busy/away due to urgent pending messages."""
    await asyncio.sleep(delay_seconds)
    self.presence_manager.transition('active', reason='saw urgent message')
    await self._process_pending_on_return()
```

#### E2.4 New method: _process_pending_on_return() in AutoChatBot

```python
async def _process_pending_on_return(self):
    """
    Process all pending messages after returning from absence.
    This is the core "realistic return" logic.
    """
    summary = self.pending_handler.get_pending_summary()
    if summary['count'] == 0:
        return

    presence = self.presence_manager.state
    reason = presence.reason

    self.logger.info(f"Processing {summary['count']} pending messages on return "
                     f"(was: {reason})")

    # 1. Optionally send return message
    return_msg = ScheduledReturn.generate_return_message(
        reason=reason,
        stage=self.stage_manager.load_relationship(self.name, self.display_name).get('stage', 'friends'),
        person_name=self.name,
        pending_messages=summary['texts'],
    )

    if return_msg:
        # Small delay before the return message (2-5 min)
        await asyncio.sleep(random.randint(120, 300))

        if self.budget.can_send():
            success = await self.send_line_message(return_msg)
            if success:
                self.budget.record_sent()
                self.add_message("you", return_msg)
                log_message(self.display_name, "OUT", return_msg,
                            metadata={"source": "return_message"})

    # 2. Wait a realistic interval before responding to pending messages (3-10 min)
    await asyncio.sleep(random.randint(180, 600))

    # 3. Process pending messages as a batch (reuse existing flow)
    pending_texts = self.pending_handler.get_all_texts()
    self.pending_handler.clear()

    if pending_texts and self.auto_respond_enabled and self.budget.can_send():
        self.pending_messages = pending_texts
        await self.process_queued_messages()
```

#### E2.5 Modified proactive_check_loop() - line 964

**Current**: Checks every hour if we should proactively message.

**New**: Also handles presence auto-transitions and return scheduling.

```python
async def proactive_check_loop(self):
    await self.discord_ready.wait()
    self.logger.info("ProactiveScheduler + PresenceManager loop started")

    while True:
        try:
            await asyncio.sleep(900)  # CHANGED: check every 15 min instead of 60

            # ===== NEW: Presence auto-transitions =====
            auto = self.presence_manager.check_auto_transitions()
            if auto:
                new_status, reason, return_min = auto
                old_status = self.presence_manager.current_status()

                # If transitioning away from active during conversation, send exit msg
                if old_status == 'active' and new_status in ('busy', 'away', 'sleeping'):
                    # Check if conversation was active
                    buffer_list = list(self.conversation_buffer)
                    hours_since = self._hours_since_last_message()
                    if (hours_since is not None and hours_since < 0.5
                        and GracefulExit.should_send_exit_message(
                            buffer_list, hours_since * 60)):
                        exit_msg = GracefulExit.generate_exit_message(
                            reason=reason,
                            stage=self.stage_manager.load_relationship(
                                self.name, self.display_name).get('stage', 'friends'),
                            person_name=self.name,
                        )
                        if exit_msg and self.budget.can_send():
                            # Small delay (1-3 min) before exit message
                            await asyncio.sleep(random.randint(60, 180))
                            success = await self.send_line_message(exit_msg)
                            if success:
                                self.budget.record_sent()
                                self.add_message("you", exit_msg)
                                log_message(self.display_name, "OUT", exit_msg,
                                            metadata={"source": "graceful_exit"})
                                self.presence_manager.transition(
                                    new_status, reason=reason,
                                    return_minutes=return_min,
                                    exit_message_sent=True)
                                continue

                self.presence_manager.transition(
                    new_status, reason=reason,
                    return_minutes=return_min)
                self.logger.info(f"Presence: {old_status} -> {new_status} ({reason})")

            # ===== NEW: Check if return time has passed =====
            if self.presence_manager.check_return_time():
                self.logger.info("Presence: returned to active")
                await self._process_pending_on_return()

            # ===== NEW: Check pending urgent messages =====
            if self.pending_handler.should_wake_early(
                    self.presence_manager.current_status()):
                early_delay = random.randint(5, 15) * 60
                self.logger.info(f"Urgent pending detected, early return in {early_delay//60}min")
                self.presence_manager.transition('active', reason='urgent message')
                await asyncio.sleep(early_delay)
                await self._process_pending_on_return()

            # ===== Existing proactive messaging (only when active) =====
            if self.presence_manager.current_status() != 'active':
                continue

            if not self.auto_respond_enabled:
                continue

            if not self.budget.can_send():
                continue

            # Existing proactive check (unchanged from here)
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
                # ... existing proactive send logic unchanged ...
                pass

        except Exception as e:
            self.logger.error(f"Loop error: {e}")
```

#### E2.6 New helper: _hours_since_last_message()

```python
def _hours_since_last_message(self) -> float | None:
    """Hours since the most recent message in conversation buffer."""
    if not self.conversation_buffer:
        return None
    last = self.conversation_buffer[-1]
    time_str = last.get('time', '')
    if not time_str:
        return None
    try:
        last_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M').replace(tzinfo=JST)
        return (datetime.now(JST) - last_time).total_seconds() / 3600
    except ValueError:
        return None
```

#### E2.7 Modified delayed_respond() - line 674

Add presence check after wake:

```python
async def delayed_respond(self, messages, delay_seconds, ...):
    delay_min = delay_seconds // 60
    self.logger.info(f"Waiting {delay_min}min before responding...")
    await asyncio.sleep(delay_seconds)

    # NEW: Check if presence changed during wait
    if self.presence_manager.should_queue_response():
        self.logger.info("Presence changed to unavailable during wait, queueing")
        for msg in messages:
            self.pending_handler.enqueue(msg)
        return

    if not self.auto_respond_enabled:
        ...  # existing
    # ... rest unchanged
```

#### E2.8 Remove _is_sleep_time()

The method at line 811:
```python
def _is_sleep_time(self) -> bool:
    hour = datetime.now(JST).hour
    return 0 <= hour < 7
```
This is now fully replaced by `PresenceManager`'s sleeping state. It can be removed,
but the sleep-time check in `process_queued_messages()` (line 629-640) must be replaced
with the presence-based routing described in E2.2.

### E3. Config changes

Add optional presence config to each `{name}_config.json`:

```json
{
  "presence": {
    "enabled": true,
    "work_days": [0, 1, 2, 3, 4],
    "work_start_hour": 9,
    "work_end_hour": 18,
    "sleep_start_hour": 0,
    "wake_hour": 7
  }
}
```

If `presence.enabled` is false or the key is missing, the system falls back to
the existing TimingController behaviour with no presence states.

---

## F. Summary of All File Changes

### relationship_engine.py

| Line (approx) | Change | Description |
|---|---|---|
| 487 | MODIFY | Add `presence_action: str = ''` to StrategyDecision |
| 575 | MODIFY | Add `presence: PresenceState | None = None` param to decide() |
| 576-577 | ADD | Presence-based override block (return early if not active) |
| 2055+ | ADD | PresenceState dataclass (~15 lines) |
| 2070+ | ADD | PresenceManager class (~120 lines) |
| 2190+ | ADD | GracefulExit class (~100 lines) |
| 2290+ | ADD | ScheduledReturn class (~100 lines) |
| 2390+ | ADD | PendingMessage dataclass (~10 lines) |
| 2400+ | ADD | PendingResponseHandler class (~100 lines) |

**Total new lines: ~445**

### auto_chat_bot.py

| Line (approx) | Change | Description |
|---|---|---|
| 145-146 | ADD | Initialize presence_manager and pending_handler |
| 555-560 | ADD | Presence check block at start of process_queued_messages |
| 601 | MODIFY | Pass presence to strategy_engine.decide() |
| 629-640 | REMOVE | Old _is_sleep_time() block (replaced by presence) |
| 674-680 | MODIFY | Add presence check in delayed_respond() |
| 811-813 | REMOVE | _is_sleep_time() method |
| after 810 | ADD | _early_return() method (~10 lines) |
| after 820 | ADD | _process_pending_on_return() method (~50 lines) |
| after 830 | ADD | _hours_since_last_message() method (~15 lines) |
| 964-1050 | MODIFY | Expand proactive_check_loop (presence + return scheduling) |

**Total new lines: ~120, modified: ~40, removed: ~15**

### New files

| File | Description |
|---|---|
| `{name}_presence.json` | Persisted presence state (1 per bot) |
| `{name}_pending_queue.json` | Pending message queue (1 per bot) |

---

## G. Behavioral Examples

### Example 1: Normal evening conversation

```
20:00 JST  PresenceManager: status=active
20:05      Laura sends "hey whats up"
20:05      process_queued_messages() -> presence=active -> normal flow
20:08      Bot responds "not much just chilling, you?"
20:10      Laura: "same haha just got home from work"
20:12      Bot: "nice, long day?"
...
22:15      PresenceManager auto-transition check fires
22:15      check_auto_transitions() -> ('away', 'winding down', 45)
22:15      GracefulExit: conversation was active 3 min ago -> send exit
22:16      Bot: "getting sleepy.. gonna head to bed"  (delay 1min)
22:16      PresenceManager: busy->away, return_at=23:00
22:30      Laura: "ok good night!"
22:30      PendingResponseHandler: queued (status=away)
23:00      check_return_time() -> but it's late, auto-transition fires
23:05      PresenceManager: away->sleeping
           (no response to "ok good night" - natural, she said goodnight)

07:15 next day  PresenceManager: sleeping->active (wake)
07:15      _process_pending_on_return()
07:17      Bot: "morning" (or combined with reply to pending)
```

### Example 2: Urgent message during work

```
09:15      PresenceManager: active->busy (work starting)
09:16      GracefulExit: conversation was cold (2h since last msg) -> no exit msg
10:30      Laura: "hey are you free to talk?"
10:30      PendingResponseHandler.enqueue() -> urgency=normal
10:45      Laura: "i really need someone to talk to right now 😢"
10:45      PendingResponseHandler.enqueue() -> urgency=high (emotional)
10:50      should_wake_early() -> True (5 min since urgent)
10:55      early_return: presence->active
10:57      _process_pending_on_return()
           -> No return message (70% skip when pending exist)
           -> Process ["hey are you free to talk?", "i really need..."] as batch
11:00      Bot responds to both messages naturally
```

### Example 3: No conversation, proactive initiation

```
18:00      PresenceManager: busy->active (finished work)
18:00      Last message in buffer was 26 hours ago
18:00      proactive_check_loop: presence=active, check ProactiveScheduler
18:00      ProactiveScheduler.check_and_initiate() -> returns opener
18:02      Bot: "just got off work, how was your day?"
```

---

## H. Constraints and Compatibility

1. **File location**: All new code in `relationship_engine.py` and `auto_chat_bot.py` only.
   No file moves or renames. (file_structure_rule compliance)

2. **JST basis**: All timestamps, hour checks, and auto-transitions use `JST = ZoneInfo('Asia/Tokyo')`.
   (Principle 7 compliance)

3. **All bots**: The system is person-agnostic. Each bot instance gets its own
   `{name}_presence.json` and `{name}_pending_queue.json`. No hardcoded person names.

4. **Budget**: GracefulExit and ScheduledReturn messages consume budget (record_sent).
   PendingResponseHandler processing also goes through the normal budget check.

5. **Backwards compatible**: If `presence.enabled` is false in config, the old
   TimingController + _is_sleep_time() behaviour is preserved. The presence_manager
   defaults to 'active' state and never transitions.

6. **ProactiveScheduler**: Still runs, but only when `presence=active`. The hourly check
   is reduced to 15-minute intervals to support presence transitions, but the
   ProactiveScheduler's own time-since-last-message check still applies.

7. **conversation_buffer**: No changes to the buffer format. Existing `.{name}_conversation_buffer.json`
   files continue to work.

8. **config.json**: New `presence` key is optional. Missing = disabled (old behaviour).
