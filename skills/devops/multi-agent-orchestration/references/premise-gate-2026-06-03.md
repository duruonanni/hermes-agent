# Premise Gate — Why Pipeline Amplified a Hallucination

**Date:** 2026-06-03
**Session:** Multi-user memory isolation design
**Models involved:** Hermes (DS Flash) → MiMo V2.5 Pro → DS V4 Pro

## The Chain

1. Hermes loaded `personal-assistant-multi-user` skill
2. Skill had agent-written template examples: `[user:duro]` with fabricated tone preferences
3. Hermes treated these as implemented facts
4. Hermes delegated to MiMo Pro: "evaluate multi-user memory isolation plan"
   - Context included the fabricated tone premises
   - MiMo produced detailed analysis based on them
5. Hermes delegated to DS V4 Pro: "evaluate from architecture perspective"
   - Context also included the fabricated premises
   - DS Pro produced detailed architecture analysis based on false premise
6. Total: 740K input tokens consumed, three models, all analyzing a non-existent problem

## Root Cause

- No premise verification step existed in the delegation pipeline
- Skill example content had no provenance marking — looked indistinguishable from user facts
- The "verify before asserting" rule only covered file/config existence, not premise soundness

## Detection Checklist

Before delegating to any model, ask:
- [ ] Is there any user preference/fact in my context that came from a skill example (not from actual files or user statements)?
- [ ] Have I read the actual USER.md/MEMORY.md on disk, or am I relying on what a skill says they contain?
- [ ] If the premise is wrong, will the downstream analysis still be useful? (If no — verify first.)
- [ ] Did the user actually confirm this, or did I/another agent assume it?
