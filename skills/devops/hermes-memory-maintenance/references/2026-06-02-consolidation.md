# Memory Consolidation — 2026-06-02

## Before

- MEMORY.md: **5,628 chars / 40 lines** — 13% over 5K limit
- USER.md: **2,704 chars / 16 lines** — within 2.5K limit

## Actions Taken

1. **Deleted 9 entries** fully covered by existing skills:
   - Feishu WebSocket heartbeat → `hermes-gateway-platforms`
   - Gateway restart safety path → `hermes-gateway-platforms`
   - tesserocr installation details → `ocr-and-documents`
   - MiMo pricing snapshot → `xiaomi-mimo-api`
   - Hermes Dashboard build/start → `hermes-dashboard`
   - Kanban plugin details → `hermes-dashboard`
   - 4× Docker headless Chrome entries → `headless-chrome-screenshot`

2. **Merged 2 entries**: DeepSeek-not-multimodal + hallucination-prevention principle → one entry

3. **Compressed 7 entries**: Format constraints, image routing, pricing rules, girlfriend info, cron job ID, CDP details

4. **Added Skill Index**: A reference list at the bottom mapping topics → skill names for future lookups

5. **Deleted USER.md duplicate**: Entry #9 (check community before suggesting) merged into #1

## After

- MEMORY.md: **1,617 chars / 12 entries** — 68% free (3,383 of 5K)
- USER.md: **2,473 chars / 8 entries** — trimmed 9%

## Key Lessons for Future Sessions

- **Priority order for consolidation**: skills-covered-data first (biggest gains), then cross-file dedup, then compression
- **Feishu delivery on memory-review cron**: Even without markdown tables, [99992402] can fail. Read from `~/.hermes/cron/output/<job_id>/` to get the report
- **Search `§` separators** to count entries, not just line count
- **Keep a Skill Index line** so the agent knows which skill to load. Don't rely on agents searching filesystem for every skill query
