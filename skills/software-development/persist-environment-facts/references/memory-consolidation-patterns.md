# Memory Consolidation Patterns

Concrete examples from an actual consolidation pass on a Hermes instance running DeepSeek V4 Flash with Feishu gateway.

## Before: 99% capacity (2,146/2,200 chars) — 11 entries

Common anti-patterns that caused overflow:

| Anti-pattern | Example | Char cost | Fix |
|---|---|---|---|
| **Triple redundancy** | "飞书不能通过MEDIA:/path发图" appeared in 3 different memory entries (line 1, 15, 17) and also in USER.md | ~400 chars across 4 locations | Merge into one entry, pick one store |
| **Static knowledge in memory** | Skill format spec (18 lines, YAML frontmatter template, agentskills.io URL) | ~393 chars | Doesn't belong in memory at all — tool behavior already encodes this |
| **Script implementation details** | "check_deepseek_balance.py查/user/balance+历史数据算日消耗（均~¥6-7），不用¥0.002/次瞎估" — internal script logic | ~170 chars | Scripts and their internal logic aren't memory facts; just keep "cron job ID X runs script Y at Z" |
| **Overfull pricing data** | MiMo pricing with per-model breakdown (4 lines) | ~359 chars | Vital to keep, but can be half the length: "MiMo V2.5 ¥2/M tokens, Pro ¥6/M tokens" is sufficient since script fetches live data |
| **Redundant user preferences** | "避免幻觉/定价必须抓取" in both MEMORY.md and USER.md | ~200 chars across 2 locations | Keep in the store where the rest of that category lives |

## After: 30% capacity (1,500/5,000 chars) — 8 entries

### What was removed entirely:
- Skill format YAML template (→ removed, tool behavior covers it)
- Skills Hub intro (→ removed, covered by hermes-agent skill)

### What was merged:
- 3 separate Feishu MEDIA restriction entries → 1
- "避免幻觉" + "定价必须抓取" + user preferences → merged into one "核心规则"
- USER.md girlfriend info → removed (already in MEMORY.md)

### What was shortened:
- MiMo pricing 359→150 chars
- Cron job detail 329→120 chars
- Feishu WebSocket + config.yaml 222→145 chars

## Consolidation heuristic

When memory exceeds 85%, scan for:

1. **Duplicate info across MEMORY.md and USER.md** — pick one target, remove from the other
2. **Verbose entries about tools/APIs/format specs** — static knowledge that should be a skill
3. **Narrative script descriptions** — keep only job ID + purpose, not internal logic
4. **Over-detailed pricing/versions** — if a script fetches this live, just note that it exists

## Expand vs consolidate decision tree

```
Memory >85%?
├─ Yes → Scan for redundancies / static knowledge
│   ├─ Found → consolidate, then recheck
│   └─ None found → expand limit (hermes config set memory.memory_char_limit 5000)
└─ No → OK
```

## Proactive maintenance: auto-review cron job

Instead of waiting for overflow, set up a weekly cron job that audits memory content:

```yaml
schedule: 0 3 * * 1       # Monday 03:00 local time
toolsets: [file]           # only needs read access
```

The cron agent reads MEMORY.md and USER.md, then reports:
- Redundant or stale entries
- Content that should be moved to a skill
- Consolidation opportunities

**Do NOT** let the cron agent write directly to memory — it should only analyze and report. Direct writes skip user approval and can accidentally delete important context.
