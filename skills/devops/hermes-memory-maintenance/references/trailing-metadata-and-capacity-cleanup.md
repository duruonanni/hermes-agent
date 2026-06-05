# Trailing Metadata Cleanup & Capacity Management

## Context

During the 2026-06-03 memory hallucination audit, two optimization opportunities emerged:

## 1. Trailing Metadata (MEMORY.md)

**Problem:** MEMORY.md had a 376-byte trailing paragraph **after the final `§` delimiter** — a past-tense restructuring log describing the 4→5 GATE rules upgrade. This content:
- Sits outside the `§`-delimited entry structure
- Gets parsed as regular memory content but has zero operational value (quality score 2/4 — informational only, no actionable directive)
- Is pure history — the restructuring already happened, its description serves no purpose

**Detection:** Check for content after the last `§` line in MEMORY.md:
```bash
sed -n '/^§$/,$ p' ~/.hermes/memories/MEMORY.md | tail -n +2
```

**Pattern to look for:**
- Change-log entries: "restructured YYYY-MM-DD: replaced X with Y... Saved N% tokens"
- Past-tense narratives about what was done
- Any content that describes a completed action without instructing future behavior

**Cleanup:** Delete these lines. The restructuring is already reflected in the GATE-style rules themselves — the change log is redundant.

**Yield:** Typically 300-400 chars recovered.

## 2. Behavioral Rules Consolidation (USER.md)

**Problem:** 9 separate rules at ~880 chars total. Three natural merge opportunities:

| Original rules | Merged into | Saving |
|---------------|-------------|--------|
| #1 (Output style) + #8 (Progress) | **Reporting** — todo list at start, before/after comparison, completed/cancelled marks | ~90 chars |
| #2 (Exploration) + #4 (Feature Discovery) + #5 (Web Search) | **Research** — GitHub chain (README→releases→docs→issues), English communities first, same-category/multi-region/multi-protocol | ~150 chars |

**Result:** 9 rules → 6 rules, savings ~300-400 chars while preserving all directives.

## 3. Capacity Expansion

When `user_char_limit: 2500` is nearly full (91%+):

- Increase to 3000 for a 3-4 month runway
- Each 500-char increment adds < 200 tokens per session — negligible cost
- Config path: `config.yaml` → `memory.user_char_limit`
- Also update `scripts/memory_review.py` defaults if they hardcode 2500
