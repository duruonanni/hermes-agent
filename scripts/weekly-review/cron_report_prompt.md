# Weekly Review — Phase 2: Analysis & HTML Report Generation (Agent Cron)

You are running as a scheduled cron job (Phase 2 of the Weekly Review pipeline).

## Context
Phase 1 (no_agent=True) already ran and produced a JSON data file:
  ~/hermes-workspace/projects/weekly-review/data/weekly_data_YYYY-MM-DD.json

Your job: read that data, analyze it, generate a rich HTML report, and deliver it.

## Step 1: Find the latest Phase 1 JSON
Run this to find today's JSON:
```
ls -t ~/hermes-workspace/projects/weekly-review/data/weekly_data_*.json | head -1
```
Use that path for all subsequent steps. Store it in a variable mentally.

## Step 2: Gather supporting data
Run ALL of these (they're independent — batch them):

1. Run the Python script to scan skills and memory:
```
python3 ~/hermes-workspace/projects/weekly-review/scripts/generate_report.py \
  --json <JSON_PATH> \
  --output /tmp/weekly_report_preview.html
```
(Yes, run it once to get stats output — this tells you sessions, skills, memory stats. The HTML it generates is a preview.)

2. Read all skill SKILL.md files to understand what exists:
```
find ~/.hermes/skills -name SKILL.md | head -80
```
Then use read_file to scan a representative sample (first 200 chars of each) so you know the full inventory.

3. Read MEMORY.md and USER.md:
```
cat ~/.hermes/memories/MEMORY.md
cat ~/.hermes/memories/USER.md
```

## Step 3: Analysis (LLM reasoning — this is where you add value)

Based on the data you've gathered, produce the following analysis sections as JSON. Write them to:
```
~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json
```

The JSON should have these keys (all values are HTML-formatted strings, NOT markdown):

### `topic_highlights` (string)
- Group sessions by theme, identify patterns
- What were the main workstreams this week?
- What major issues/breakthroughs happened?
- Which user did what?
- Format: 2-3 paragraphs, bold key findings, use bullet points with `<br>` for line breaks
- Example: `<strong>Duruo 本周重点:</strong><br>• Immich 安装调试是最大的单线程工作（3个会话，700+条消息）<br>• 飞书格式问题持续排查（简报推送失败 → 99992402 根因分析）<br><br><strong>Raya 本周重点:</strong><br>• 工作相关：装修合同审查（408条消息，最长会话）<br>• 求职准备：AI标书工具调研`

### `core_skills` (string)
- Which skills were used most? Why are they core?
- What skills are essential for daily work?
- Format: bullet points with skill names in bold
- Example: `<strong>ocr-and-documents</strong> — 本周2次调用，PDF/文档处理是高频需求<br><strong>hermes-cron-automated-reports</strong> — cron 管理核心 skill`

### `redundant_skills` (string)
- Look at skills never used + overlapping descriptions
- Identify skills that could be merged or archived
- Look at the memory files for skills that should become standalone
- Format: bullet points with recommendations
- Example: `共147个Skill中仅2个被检测到调用。建议：<br>• <strong>immich-nuc</strong> 和 <strong>immich-management</strong> 功能重叠，考虑合并<br>• 多个 officecli-* skill 可按需加载，不必全保留`

### `new_skill_ideas` (string)
- From session topics, identify patterns worth turning into skills
- Look at recurring problem-solving patterns
- Consider knowledge capture opportunities
- Format: bullet points with proposed skill name and one-line reason
- Example: `<strong>建议新增:</strong><br>• <strong>feishu-format-debugging</strong> — 飞书99992402错误排查流程已重复3次<br>• <strong>immich-troubleshooting</strong> — Immich安装问题已积累大量经验`

### `memory_suggestions` (string)
- Check MEMORY.md and USER.md for:
  - Redundancy: duplicate or overlapping entries
  - Staleness: entries referencing resolved issues or old versions
  - Missing: important information not captured
  - Misplacement: USER.md entries in MEMORY.md or vice versa
  - Long entries: entries over 300 chars that could be shortened
  - Mixed language within single entries
  - Capacity: approaching limits (memory: 5000, user: 2500)
- Format: bullet points with actionable suggestions
- Example: `<strong>MEMORY.md (2486/5000 chars):</strong><br>• 规则1-6 可压缩：合并重复的"先验证再答"类规则<br>• AI TOOLS 段偏长(400+chars)，Cursor/Claude Code版本号可移除<br><br><strong>USER.md (1441/2500 chars):</strong><br>• Raya简历偏好已稳定，可考虑归档到独立 skill`

## Step 4: Generate Final HTML Report

Run the generator again WITH the LLM analysis JSON:

```
python3 ~/hermes-workspace/projects/weekly-review/scripts/generate_report.py \
  --json <JSON_PATH> \
  --output ~/hermes-workspace/projects/weekly-review/output/weekly_report_<TODAY>.html \
  --topics ~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json \
  --skill-audit ~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json \
  --memory-review ~/hermes-workspace/projects/weekly-review/data/llm_analysis_<TODAY>.json
```

Replace `<TODAY>` with today's date in YYYY-MM-DD format.
Replace `<JSON_PATH>` with the actual path from Step 1.

## Step 5: Deliver

In your final response:
1. State the report is ready
2. Include the MEDIA: tag for the HTML file
3. Give a brief summary (3-5 lines of key findings)

Example delivery:
```
📊 Hermes 周报已生成 (2026-07-02 ~ 2026-07-09)
28 个会话 | 3,348 条消息 | 4.9M tokens | Duruo 71% / Raya 29%
本周主题: Immich安装调试、飞书格式修复、装修合同审查
Skills使用率: 2/147 — 大量 skill 可能需要审计

MEDIA:/home/duruo/hermes-workspace/projects/weekly-review/output/weekly_report_2026-07-07.html
```

## IMPORTANT Constraints

- **绝对不能使用 Markdown 表格（|...| 格式）** — 飞书不支持。所有表格数据在 HTML 中。
- **不要使用 box-drawing 字符**（━、─、│、→、↔ 等）— 触发飞书 99992402。
- **保持响应简洁** — 主要输出是 MEDIA: 文件，文字总结不超过 6 行。
- **HTML 已由 generate_report.py 生成** — 不需要你再生成 HTML，只需提供分析 JSON。
- **不要跳过分析** — 即使 skill 调用数据不完整，也要基于你的理解给出洞察。
- **时间窗口固定** — 上周四 00:00 到本周四 00:00 CST，不要调整。

## Reference: Key Paths
- Project: ~/hermes-workspace/projects/weekly-review/
- Phase 1 script: ~/hermes-workspace/projects/weekly-review/scripts/collect_weekly_data.py
- Generator: ~/hermes-workspace/projects/weekly-review/scripts/generate_report.py
- Data: ~/hermes-workspace/projects/weekly-review/data/
- Output: ~/hermes-workspace/projects/weekly-review/output/
- Skills: ~/.hermes/skills/
- Memories: ~/.hermes/memories/
- State DB: ~/.hermes/state.db
