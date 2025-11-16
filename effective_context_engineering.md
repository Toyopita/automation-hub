---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
---

# Effective Context Engineering for AI Agents

Anthropic Engineering
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

---

## What is Context Engineering?

**Context** = The set of tokens included when sampling from an LLM

**Context Engineering** = Optimizing token utility against LLM constraints to achieve desired outcomes consistently

---

## Context Engineering vs. Prompt Engineering

**Prompt Engineering:**
- Writing effective instructions

**Context Engineering:**
- Curating optimal tokens during inference across multiple turns
- Managing entire context state:
  - System instructions
  - Tools
  - External data
  - Message history

---

## Why Context Engineering Matters

### Context Rot
- LLM accuracy diminishes as tokens increase
- Models have finite "attention budgets" (like human working memory)
- Transformer architecture creates n² pairwise token relationships
- Performance degradation at scale

---

## The Anatomy of Effective Context

### 1. System Prompts

**Balance is key:**
- ❌ Overly brittle hardcoded logic
- ❌ Vague guidance
- ✅ Clear sections with XML/Markdown headers
- ✅ Start minimal, add based on failure modes

---

## The Anatomy of Effective Context

### 2. Tools

**Token-efficient & promote efficiency:**
- ❌ Bloated toolsets with overlapping functionality
- ❌ Ambiguity in tool selection
- ✅ Minimal, focused tool descriptions
- ✅ Clear purpose for each tool

---

## The Anatomy of Effective Context

### 3. Examples

**Quality over quantity:**
- ✅ Curate diverse canonical examples
- ❌ Exhaustive edge cases
- 💡 "Examples are the pictures worth a thousand words"

---

## Context Retrieval Strategies

### Just-in-Time Approach

**Like human cognition:**
- Maintain lightweight identifiers (file paths, links)
- Dynamically load data at runtime using tools
- Use external systems rather than memorizing everything

---

## Context Retrieval Strategies

### Hybrid Strategy

**Best of both worlds:**
1. Retrieve some data upfront for speed
2. Pursue autonomous exploration as needed

**Example:** Claude Code
- Drops CLAUDE.md files initially
- Uses glob/grep for just-in-time retrieval

---

## Long-Horizon Task Techniques

### 1. Compaction

**Summarize conversations nearing context limits:**
- Preserve architectural decisions
- Preserve critical details
- Discard redundant tool outputs
- Reinitiate with compressed summaries

---

## Long-Horizon Task Techniques

### 2. Structured Note-Taking

**Persistent notes outside context windows:**
- Enables multi-hour coherence
- Survives summarization resets

**Example:** Claude playing Pokémon
- Maintained strategic notes across thousands of steps

---

## Long-Horizon Task Techniques

### 3. Sub-Agent Architectures

**Specialized agents with clean context windows:**
- Main agent coordinates workflow
- Sub-agents handle focused tasks
- Return condensed summaries (1,000-2,000 tokens)

---

## Closing Guidance

> "Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome."

**Remember:**
- Context is a precious finite resource
- Requires thoughtful curation
- Even as models improve, context management remains critical

---

## Key Takeaways

1. Context engineering ≠ Prompt engineering
2. Manage "attention budget" carefully
3. Balance system prompts, tools, examples
4. Use just-in-time retrieval strategies
5. Apply compaction, note-taking, sub-agents for long tasks
6. Quality tokens > Quantity tokens

---

# Thank you!

**Source:** Anthropic Engineering Blog
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
