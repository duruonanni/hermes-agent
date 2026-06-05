# Memory Optimization Review — Cron Pattern

An agent-based cron job that periodically audits MEMORY.md and USER.md for redundancy, stale entries, and skill-archivable content.

## When to Use
- Memory utilization approaching 80%+
- User reports "you forgot X" or "this info was there before"
- After a burst of skill creation / config changes

## Architecture

```
Weekly cron job (agent-based, no_agent=False, Monday 03:00 BJT)
  │
  ├── 1. Read MEMORY.md and USER.md
  │
  ├── 2. Analyze for:
  │      ├── Redundant entries (same fact duplicated)
  │      ├── Skill-archivable content (stable procedures → SKILL.md)
  │      ├── Compression candidates (overly verbose entries)
  │      └── Stale/outdated entries
  │
  ├── 3. Produce structured report
  │
  └── Deliver to origin chat (read-only — no modifications)
```

## Key Rules for the Cron Agent

- **Read-only review** — never modify memory files
- **Forbid Markdown tables** in output (causes Feishu [99992402] delivery failure)
- **Format**：粗体标签 + 缩进列表，不出现 `|` 字符
- Flag actionable items with `🛠` marker so user can ask the agent to execute

## Output Format Template

```
**去冗余发现**
- **A组**：条目 #3 和 #5 语义重叠 → 建议合并
- **B组**：条目 #10 和 #12 重复 → 建议删除 #12

**可归档建议**
- **条目 #2**: tesseract 安装 → 已有 skill:ocr-and-documents，可删除记忆

**压缩建议**
- **条目 #1**: 当前46字 → 可精简为「...」

**过时检查**
- **条目 #X**: 内容... → 建议保留/删除

**容量预警**
- MEMORY.md: X / Y chars（超载Z%）
- 执行建议后可释放约 N 字符
```

## Pitfalls
- **MEMORY.md may be oversized** — read it as a raw file, not via the `memory` tool (which may truncate at the character limit)
- **Feishu [99992402] error** ALWAYS means the output contained a Markdown table. The cron agent must explicitly be told not to use `|` characters.
- **User.md has a separate char limit** — check both files independently
- The review consumes ~500 tokens per run for the LLM analysis
