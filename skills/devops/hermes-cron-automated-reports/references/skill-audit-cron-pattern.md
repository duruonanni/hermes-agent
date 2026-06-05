# Skill Maintenance Audit — Cron Pattern

An agent-based cron job that periodically scans custom skills for issues and auto-fixes clear-cut problems.

## When to Use
- User has multiple custom skills (10+)
- Skills were created over time and may have broken cross-references
- Need to detect merge candidates, stale pricing, or hallucinated references

## Architecture

```
Weekly cron job (agent-based, no_agent=False, Monday 03:30 BJT)
  │
  ├── 1. List custom skills (in ~/.hermes/skills/ but NOT hermes-agent repo)
  │
  ├── 2. For each SKILL.md:
  │      ├── Check cross-references (`` `skill-name` `` patterns)
  │      ├── Check for deleted-skill references
  │      └── Check for internal file references that don't exist
  │
  ├── 3. Apply auto-fixes:
  │      └── For broken cross-references → patch with correct skill name
  │
  ├── 4. Report:
  │      ├── Fixed items
  │      ├── Merge candidates (user decides)
  │      └── Stale pricing flags
  │
  └── Deliver to origin chat
```

## Key Rules for the Cron Agent

- **Auto-fix broken cross-references only** — do NOT merge skills autonomously
- **Flag merge candidates** with clear reasoning, let the user decide
- **Check pricing freshness** in API skills (deepseek-api, xiaomi-mimo-api)
- **Output format**: no Markdown tables (Feishu delivery fails on tables)

## Prompt Template

```
# Weekly Custom Skill Maintenance Audit

## Task
Scan and maintain the custom skills created for this NUC environment. 
Identify issues, fix clear-cut problems, and report.

## Background
Custom skills live in ~/.hermes/skills/. Built-in from Hermes Agent = ~/.hermes/hermes-agent/skills/.
Custom = in ~/.hermes/skills/ but NOT in hermes-agent repo.

## Checklist
1. **Verify Cross-References** — check for `` `skill-name` `` references to deleted skills
2. **Check Merge Candidates** — overlapping scope by name/description
3. **Check Stale Content** — API pricing may be outdated
4. **Apply Clear Fixes** — broken cross-refs → patch. Do NOT merge autonomously.

## Output
No markdown tables. Use:
- **技能数**: count
- **修复**: what was patched
- **合并建议**: merge candidates
- **其他**: anything unusual
```

## Delivery

`deliver=origin` — report goes to wherever the job was created from.
Feishu-compatible format (no tables) required for successful delivery.

## Pitfalls
- **Cron agent sees MEMORY.md/USER.md in memory injection** — may cause confusion with memory-review job
- `verify-system-state` skill is useful to load for state verification (Docker, CDP, MCP health)
- **Price info ages fast** in Chinese AI market (MiMo, DeepSeek both changed pricing recently)
- **[Errno 32] Broken pipe in cron** — do NOT chain shell pipelines (`find | xargs | grep | sed`) in agent-driven cron terminal() calls. The pipe reader (cron delivery system) closes its side when output exceeds buffer, causing the writer to crash. Always redirect command output to a temp file with `>` and read with `read_file()`. Use separate `terminal()` calls per command, not `&&`/`|` chains in one call.
