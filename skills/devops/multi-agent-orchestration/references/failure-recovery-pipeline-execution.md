# Failure-Recovery: Pipeline Execution After Skipping

Date: 2026-06-03
Source: Real session — user asked about multi-user memory isolation

## What Happened

1. **User asked**: "如何让Hermes同时服务两个用户，共享Skill，记忆准确区分不混淆不出现幻觉"
2. **Agent response**: Immediately started researching and giving a 3-layer solution proposal — no pipeline, no multi-agent evaluation
3. **User correction**: "为什么你直接下结论了" and "为什么 multi-agent-orchestration 没有生效"
4. **Agent recovery**: Loaded the skill, self-checked, admitted mistake, then executed the full pipeline correctly

## Root Cause Chain

```
Rule 7 trigger condition too narrow → Agent didn't recognize task as matching
  → Didn't load multi-agent-orchestration skill
  → Went straight to "I'll figure this out" mode
  → User called it out
```

Sub-root-cause: Agent had already loaded `personal-assistant-multi-user` skill and thought "that's enough" — missed the need to also load the orchestration skill. Multiple overlapping skills = load them ALL, not the first one that fits.

## Recovery Pattern (what worked)

1. **Acknowledge the failure immediately** — don't defend, don't explain why you thought it was fine
2. **Investigate the root cause** — in this case: MEMORY.md rule 7 was too narrow, skill had a naming collision
3. **Fix the artifacts** — broaden rules, update skill triggers, resolve name collision
4. **Re-execute the pipeline correctly** — delegate to researcher + architect
5. **Synthesize** — summarize both model outputs and present to user

## Self-Check Checklist (for future sessions)

Before giving any conclusion on a non-trivial question:

- [ ] Did I just give a direct answer without checking rule 7 triggers?
- [ ] Did I skip loading a skill because I thought I already knew enough?
- [ ] Am I about to say something about a user's name, tone, or preference that I haven't verified against actual disk files?
- [ ] Did I just treat a skill's example/template block as if it were actual implemented content?

If any answer is "yes" or "maybe", pause and execute the pipeline.

## Key Takeaway

The most dangerous moment for an orchestration agent is when it thinks "I can handle this one myself." The self-check mechanism exists specifically to catch this. Trust it.
