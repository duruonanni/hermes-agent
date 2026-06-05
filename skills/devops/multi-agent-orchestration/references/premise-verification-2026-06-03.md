# Premise Verification Failure — 2026-06-03

## What Happened

Agent loaded `personal-assistant-multi-user` skill, saw `[user:duro]`/`[user:raya]` tone example blocks in Problem 1's solution section, treated them as user-confirmed facts, then delegated to MiMo + DS Pro for multi-model analysis based on that false premise.

## Chain

```
skill template example (Agent-written, not user-confirmed)
  → treated as fact by later agent session
  → delegated to MiMo: "evaluate this multi-user tone proposal"
  → delegated to DS Pro: "evaluate from architecture angle"
  → both produced lengthy analyses of a non-existent problem
  → agent presented to user as "multi-model evaluation"
```

## Root Cause

No premise verification step exists between "I have context" and "I delegate to another model." The pipeline executed perfectly — loaded skill, delegated to right models, summarized results — but the input was garbage.

## Fix Applied

- `multi-agent-orchestration` skill: Added Trap 2 (前提未验就委派) with 3-step defense
- `personal-assistant-multi-user` skill: WARNING added at Problem 1 solution section
- MEMORY.md: Existing rules 2+3 cover identity priority

## Self-Check Questions Before Any Delegation

1. What are the key factual claims in my context?
2. Did each claim come from user, from a skill template, or from my own inference?
3. Can I verify each claim against actual files/memory before delegating?
4. If unsure about any claim — ask the user first.
