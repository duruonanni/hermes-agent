# Chain Hallucination: Skill Template → Multi-Model Pipeline on False Premise

## Date
2026-06-03, ~17:00-18:30 CST

## What Happened

1. Agent loaded `personal-assistant-multi-user` skill
2. Read `[user:duro]` template block with "语言风格：简洁务实，证据优先" and `[user:raya]` with "语言风格：热情鼓励"
3. **Treated these as Duruo's actual preferences** — despite them being Agent-written templates in a skill code block
4. Fabricated a statement: "USER.md is all Duruo's preferences, Raya would feel cold" — neither claim was true
5. Delegated to MiMo V2.5 Pro (50s, 5K tokens) for "researcher" evaluation of multi-user memory isolation
6. Delegated to DeepSeek V4 Pro (85s, 8K tokens) for "architect" evaluation  
7. Both models accepted the false premise and produced detailed analyses
8. User called it out: "语气这个事情为什么是放在 MEMORY.md?" and "热情鼓励的来源是什么?"
9. Investigation revealed:
   - SOUL.md is just the Hermes default — no user-customized tone
   - USER.md has NO tone/voice sections for either user
   - The `[user:xxxx]` blocks with "语言风格" were written by a prior agent session
   - The skill ALREADY had a WARNING about this exact pattern (line 121+) — but it was buried after the example
10. The same pattern had occurred EARLIER the same day — same skill, same fake premise, different session

## Root Causes

1. **Warning placement:** The chain-hallucination WARNING was on line 121 of a 500-line skill. The dangerous example was at line 108. The agent stopped reading before reaching the warning.
2. **Template/fact ambiguity:** Agent-written examples in skills look identical to user-confirmed facts. No metadata distinguishes them.
3. **No premise-verification step:** The multi-agent Pipeline (`load skill → delegate to MiMo/DS Pro`) has no "verify these premises are real" step.
4. **Cross-session compounding:** Error A (agent writes template) + Error B (agent reads template as fact) + Error C (agent delegates based on false premise) = 3x pipeline amplification.

## Prevention (Applied)

1. **WARNING moved to absolute top** of `personal-assistant-multi-user` SKILL.md, before all content
2. **Specific tone examples removed** from Problem 1 template — replaced with generic `[user:USERNAME]` placeholders
3. **"FIRST: Verify Premises" section added** with 4 mandatory steps before any skill content can be used
4. **This reference file** documents the pattern so future sessions can trace it

## Related Files

- `SKILL.md` — top-level warning now at line ~12
- `personal-assistant-multi-user/references/error-pattern-audit.md` — broader Pattern 4: Third-Party Model Fabrication
- `../../MEMORY.md` — rule 8 pending (name cross-validation)
