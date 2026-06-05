# Pipeline Error Amplification — 2026-06-03

## Summary

Discovered a concrete chain hallucination pattern where skill template examples are treated as user-approved facts, then amplified through the multi-agent pipeline.

## The Chain

```
Skill file contains template examples (agent-written, user as [user:duro] placeholder)
  → Agent loads skill, treats examples as real user preferences
  → delegate_task passes false premises to subagents (MiMo, DS Pro)
  → Subagents produce confident analysis on false foundations
  → Orchestrator aggregates confidently-wrong results
  → Error amplified 2-3× vs single-agent hallucination
```

## Real Case (2026-06-03)

The `personal-assistant-multi-user` skill contained tone/behavior blocks labelled `[user:duro]` / `[user:raya]` that were Agent-written templates, not real user preferences. A future session treated them as verified user facts, built a multi-model analysis on that premise, and produced a full evaluation document with professionally-structured output — completely wrong at the foundation.

## Root Cause

Three independent failures that compound:

1. **Skill provenance blind spot** — SKILL.md content has no runtime provenance marker. The model sees all skill text as equally authoritative regardless of origin (agent-created template vs. user-documented preference).

2. **No premise verification before delegation** — `delegate_task` passes context directly without validating factual claims in that context.

3. **No cross-model premise consensus** — When MiMo and DS Pro both receive the same false premise, they both produce plausible-but-wrong analysis. Their agreement feels like validation rather than correlated error.

## The Pipe Grows

Unlike single-agent hallucination (one wrong fact, at most one wrong conclusion), pipeline amplification has multiplicative damage:

| Stage | Error type | If single agent | If pipeline (3 subagents) |
|-------|-----------|----------------|--------------------------|
| Fact assertion | Premise error | 1 wrong fact | 1 wrong fact (shared) |
| First analysis | Amplified | 1 wrong conclusion | 1 wrong conclusion |
| Second analysis | Amplified again | — | 1 wrong conclusion, new wrong dependency |
| Final summary | Confidently wrong | 1 wrong statement | 2-3 wrong statements that cross-reference each other |

## Prevention: Premise Gate

Before every `delegate_task` call, execute a Premise Gate:

```python
def premise_gate(context: str) -> str:
    \"\"\"Strip unverified claims from delegation context.\"\"\"
    # 1. Identify factual claims in context
    #    Look for: user preferences, config values, path existence, identity info
    
    # 2. Verify each against real files (read_file) or real state (terminal)
    #    Skill template examples → strip or replace with "(need user confirmation)"
    
    # 3. Return context with only verified facts
    return clean_context
```

Manual checklist (since we can't code the gate as a runtime tool yet):

```
Before delegate_task:
[ ] Context contains claims about user preferences from skills? → Verify or strip
[ ] Context contains file paths from skills? → Verify with read_file
[ ] Context contains identity info from skills? → Verify with MEMORY.md
[ ] Context contains technical assertions from skills? → Verify with terminal
```

## References

- MEMORY.md §46: Chain hallucination entry (discovered 2026-06-03)
- `personal-assistant-multi-user/SKILL.md` §23-30: WARNING about template examples
- `multi-agent-orchestration/SKILL.md`: Strengthened principle #2 with check list
