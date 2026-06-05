# Pipeline Premise Amplification (2026-06-03)

**Pattern:** Skill template examples → treated as fact → delegated to multiple models → each model builds analysis on false premise → error amplified 3-5×.

## The Failure Chain

```
Skill personal-assistant-multi-user
  └─ Contains `[user:duro]` / `[user:raya]` template examples with made-up tone preferences
      └─ Agent reads skill, treats examples as "maybe real" → includes in delegation context
          └─ MiMo V2.5 Pro receives context with false premise → produces detailed 5-point evaluation
              └─ DS V4 Pro receives context with false premise → produces architecture analysis
                  └─ Agent summarizes both → gives user a "multi-model consensus" on a non-existent problem
```

## Root Cause

The pipeline had no **premise verification gate** before delegation. Every step was technically correct (loaded skill → delegated to models → summarized output), but the first step passed garbage in, so every subsequent step amplified the garbage.

## Prevention

1. **Premise Gate:** Before ANY `delegate_task` call, review the context for claims from skill template blocks. Verify each claim against actual MEMORY.md/USER.md on disk.
2. **Context tagging:** In delegation context, separate `<verified_facts>` (confirmed by user or file read) from `<unverified_claims>` (from skill templates, model outputs, or agent assumptions).
3. **Subagent output validation:** When a subagent returns analysis that cites user preferences/names/styles, cross-check those claims against actual stored identities before accepting them.
