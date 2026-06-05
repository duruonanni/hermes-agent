# Multi-Model Evaluation: Memory Hallucination Issues (2026-06-03)

Evaluated by **DeepSeek V4 Pro** + **MiMo V2.5 Pro** + **Codex GPT 5.5** + Google Search.

## Consensus Matrix

| Issue | DeepSeek V4 Pro | MiMo V2.5 Pro | Codex GPT 5.5 | Consensus |
|-------|:-:|:-:|:-:|:-:|
| 1. Mid-Session Reload (P2) | 4 | 5 | 5 | **High** - incremental delta, not full reload |
| 2. Memory Routing #22612 (P1) | 3 | 3 | 4 | **Medium-High** - phase approach |
| 3. add() consistency checks (P1) | 5 | 2 | 3 | **Medium** - rules only, no LLM check, non-blocking |
| 4. API threshold alerts (P3) | 5 | 4 | 5 | **High** - cron-based |
| 5. USER.md capacity | 5 | 5 | 4 | **High** - clean now |
| 6. MEMORY.md trailing metadata | 5 | 5 | 5 | **Very High** - zero controversy |

## Unique Per-Model Insights

### DeepSeek V4 Pro
- The 6 issues form a **three-layer cascade**: routing layer missing → consistency layer broken → observability layer weak
- Core contradiction: ~400 chars/week linear growth vs flat-injection architecture. 8-12 weeks until system prompt hits 11K+ chars
- Recommended `/reload memory` alternative: **incremental delta** — append "Recent additions this session" to volatile block suffix, keeping frozen snapshot intact for prefix cache warmth
- Priority order (ROI): 1→3→2→4→5→6

### MiMo V2.5 Pro
- "USER.md has the wrong content boundary" — behavioral rules belong in MEMORY.md, not USER.md. 5-minute restructure frees ~35% capacity
- Truly hallucination-causing: only #1 (stale snapshot) and #3 (no semantic check — but don't block online)
- 2-hour fix package covers 70% of perceived issues
- add() consistency check: DON'T do online blocking. Use offline review (cron) + non-blocking warning instead

### Codex GPT 5.5
- "Frozen snapshot is the most impressive design decision — many frameworks (LangChain, AutoGPT) miss this critical optimization"
- Biggest architectural defect: external memory providers (mem0, honcho, hindsight) are already packaged but MemoryStore is decoupled from them. Enabling `hermes provider memory mem0` solves issues 2+3 in one step
- Semantic conflict detection is an unsolved problem across the industry — do keyword-level only

## Web Search Findings (6 actionable items)

| Finding | Source | Insight |
|---------|--------|---------|
| Hermes already has 6-layer defense | memory_tool.py source | freeze snapshot + threat scan + dedup + drift detection + capacity + file lock |
| mem0 built-in | mem0.ai | source anchoring + conflict resolution + vector search |
| hindsight reflective memory built-in | Vectorize.io | extract after task completion, not during |
| Eywa: evidence before belief | arXiv 2605.30771 | immutable evidence layer + derived belief layer separation |
| HaluMem benchmark | GitHub MemTensor | 3 task types: extraction/update/QA |
| Community consensus | Reddit r/hermesagent | temp state → session_search, skills → skill tool, memory → persistent facts only |

## Phase 0-3 Roadmap

| Phase | Items | Effort | ROI |
|-------|-------|--------|:---:|
| **0 - Quick fixes** | P0-1: delete trailing metadata (30s) | <40 min | Very High |
| | P0-2: USER.md 9→6 rules (10min) | | |
| | P0-3: API threshold alerts (30min) | | |
| **1 - Write-time consistency** | P1-1: add() keyword-level conflict warnings | 2 hours | High |
| | P1-2: mid-session incremental delta | | |
| **2 - Architecture** | P2-1: Memory Routing Phase 1 (section params) | 2-3 days | Medium-High |
| | P2-2: Memory Routing Phase 2 (dual-delimiter) | | |
| **3 - Operations** | P3-1: weekly memory review push to Feishu | Ongoing | Medium |
| | P3-2: capacity <4wk auto-alert | | |
