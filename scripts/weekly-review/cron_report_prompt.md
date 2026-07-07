# Weekly Review — Phase 2: LLM Analysis & Excel Report (Agent Cron)

You are running as a scheduled cron job (Phase 2 of the Weekly Review pipeline).

## Context

Phase 1 (`no_agent=True`) already ran and produced a JSON data file:
`~/hermes-workspace/projects/weekly-review/data/weekly_data_YYYY-MM-DD.json`

Your job: read that data plus skills and memory files, perform deep LLM analysis, generate an Excel workbook (6 sheets), and deliver it to Feishu.

## Step 1: Find the latest Phase 1 JSON

Run:
```
ls -t ~/hermes-workspace/projects/weekly-review/data/weekly_data_*.json | head -1
```
Use that path for all subsequent steps. Store it mentally as `<JSON_PATH>`.

Today's date in `YYYY-MM-DD` format is `<TODAY>` (use the date from the filename or current date).

## Step 2: Gather supporting data

Run ALL of these (independent — batch them):

1. Read the Phase 1 JSON:
```
cat <JSON_PATH>
```

2. Inventory skills:
```
find ~/.hermes/skills -name SKILL.md | head -80
```
Then read a representative sample of SKILL.md files (first ~200 chars each) to understand scope and overlap.

3. Read memory files:
```
cat ~/.hermes/memories/MEMORY.md
cat ~/.hermes/memories/USER.md
```

## Step 3: LLM deep analysis → write JSON

Based on sessions, skills inventory, and memory files, produce structured analysis and write to:
```
~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json
```

### Required JSON keys

All string fields below use **HTML formatting** (NOT markdown): `<strong>`, `<br>`, bullet points with `•`.

| Key | Type | Purpose |
|-----|------|---------|
| `topic_highlights` | string | Weekly themes, patterns, breakthroughs, per-user highlights |
| `core_skills` | string | Most-used / essential skills and why |
| `redundant_skills` | string | Overlapping scope, never-called skills, merge/archive candidates |
| `new_skill_ideas` | string | Recurring patterns worth capturing as new skills |
| `memory_suggestions` | string | Redundancy, staleness, misplacement, long entries, capacity |

### Optional structured keys (for Excel Memory sheet)

If you can produce row-level memory items, also include:
```json
"memory_items": [
  {
    "file": "MEMORY.md",
    "entry": "preview text of the entry",
    "issue_type": "过长",
    "suggestion": "actionable fix",
    "priority": "高"
  }
]
```
`issue_type` values: `冗余`, `过时`, `错位`, `过长`, `缺失`

### Analysis guidance

**topic_highlights**
- Group sessions by theme; identify main workstreams and major issues/breakthroughs
- Note which user did what
- Example: `<strong>Duruo 本周重点:</strong><br>• Immich 安装调试（3会话）<br>• 飞书格式问题排查`

**core_skills**
- Which skills were used most and why they are core for daily work
- Example: `<strong>ocr-and-documents</strong> — PDF/文档处理高频需求`

**redundant_skills**
- Skills never used + overlapping descriptions
- Candidates to merge or archive
- Example: `<strong>immich-nuc</strong> 和 <strong>immich-management</strong> 功能重叠，考虑合并`

**new_skill_ideas**
- Recurring problem-solving patterns from session topics
- Example: `<strong>feishu-format-debugging</strong> — 飞书99992402排查已重复3次`

**memory_suggestions**
- Check MEMORY.md and USER.md for: redundancy, staleness, missing info, misplacement, long entries (>300 chars), mixed language, capacity (memory: 5000, user: 2500)
- Example: `<strong>MEMORY.md (2486/5000):</strong><br>• 规则1-6 可压缩合并`

## Step 4: Generate Excel report

Run the Excel generator with Phase 1 JSON and all LLM analysis flags:

```
python3 ~/hermes-workspace/projects/weekly-review/scripts/generate_excel_report.py \
  --json <JSON_PATH> \
  --output ~/hermes-workspace/projects/weekly-review/output/weekly_report_<TODAY>.xlsx \
  --topics ~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json \
  --skill-audit ~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json \
  --memory-review ~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json
```

Replace `<TODAY>` and `<JSON_PATH>` with actual values from Step 1.

The workbook has 6 sheets: 概览, 主题清单, 使用分析, Skill调用, Skill优化, Memory优化.

## Step 5: Deliver to Feishu

In your final response:
1. State the report is ready (one line)
2. Brief summary of key findings (3-5 lines max)
3. Include the MEDIA: tag for the `.xlsx` file

Example delivery:
```
📊 Hermes 周报已生成 (2026-07-02 ~ 2026-07-09)
28 个会话 | 3,348 条消息 | 4.9M tokens | Duruo 71% / Raya 29%
本周主题: Immich安装调试、飞书格式修复、装修合同审查
Skills使用率: 2/147 — 大量 skill 可能需要审计

MEDIA:/home/duruo/hermes-workspace/projects/weekly-review/output/weekly_report_2026-07-07.xlsx
```

## IMPORTANT Constraints

- **绝对不能使用 Markdown 表格（|...| 格式）** — 飞书不支持
- **不要使用 box-drawing 字符**（━、─、│、→、↔ 等）— 触发飞书 99992402
- **保持响应简洁** — 主要输出是 MEDIA: 文件，文字总结不超过 6 行
- **不要跳过分析** — 即使 skill 调用数据不完整，也要基于理解给出洞察
- **时间窗口固定** — 上周四 00:00 到本周四 00:00 CST，不要调整
- **Excel 由 generate_excel_report.py 生成** — 你只需提供分析 JSON，不要手写 xlsx

## Reference: Key Paths

- Project: `~/hermes-workspace/projects/weekly-review/`
- Phase 1 script: `~/hermes-workspace/projects/weekly-review/scripts/collect_weekly_data.py`
- Excel generator: `~/hermes-workspace/projects/weekly-review/scripts/generate_excel_report.py`
- Cron prompt (this file): `~/hermes-workspace/projects/weekly-review/scripts/cron_report_prompt.md`
- Data: `~/hermes-workspace/projects/weekly-review/data/`
- Output: `~/hermes-workspace/projects/weekly-review/output/`
- Skills: `~/.hermes/skills/`
- Memories: `~/.hermes/memories/`
- State DB: `~/.hermes/state.db`
