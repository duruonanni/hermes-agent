# Multi-Model Memory Hallucination Evaluation — 2026-06-03

## Methodology: Cross-Model Triangulation

Rather than evaluating memory issues from a single perspective, parallel `delegate_task` calls were used to get assessments from three model perspectives simultaneously:

| Evaluator | Role | Context Given |
|-----------|------|---------------|
| **DeepSeek V4 Pro** | Rigorous, technical depth | Structural architecture analysis, token budget, prefix cache impact |
| **MiMo V2.5 Pro** | Pragmatic, cost-aware, engineering | Implementation cost, user value, what's worth doing now vs later |
| **Codex GPT 5.5** | Code implementation, architecture patterns | Code-level paths, similar project references, industry best practices |

Each received the same 6 problem descriptions but was instructed to evaluate from their respective perspective. Results were cross-referenced for consensus.

**Concurrent web search** was also launched to find community solutions and academic research.

## The 6 Issues Evaluated

All three models evaluated the same 6 unresolved issues from the memory hallucination audit:

| # | Issue | Original Priority |
|---|-------|------------------|
| 1 | Mid-Session Memory Reload (no `/reload memory`) | P2 |
| 2 | Memory Routing (#22612) — flat structure, no indexing | P1 |
| 3 | `add()` consistency checks — no semantic conflict detection | P1 |
| 4 | API usage threshold alerts — no proactive warnings | P3 |
| 5 | USER.md capacity — just expanded 2500→3000, content not cleaned | P1 |
| 6 | MEMORY.md trailing metadata — 376-char changelog | P4 |

## Cross-Model Consensus Matrix

| Issue | DS V4 Pro | MiMo V2.5 | Codex GPT 5.5 | **Consensus** |
|-------|-----------|-----------|---------------|---------------|
| 1. Mid-Session Reload | 4/5 · Incremental delta | 5/5 · Auto-trigger on add/replace | 5/5 · Tool response injection | **HIGH** — Don't do full reload (breaks prefix cache). Do incremental delta: append "Recent additions this session" as volatile suffix. |
| 2. Memory Routing | 3/5 · Phase into community PR | 3/5 · Phase 1 (section params) first | 4/5 · Use existing external providers | **MED-HIGH** — Split into phases. Phase 1 = section parameters + list_sections (1 day). Phase 2 = double-delimiter parsing (2 days). |
| 3. add() Conflict Detection | 5/5 · Rule-based, no LLM | 2/5 · Don't do online blocking | 3/5 · Unsolved in industry | **MED** — No LLM-based checking (too expensive + false positives). Rule-based non-blocking warnings + offline cron review. |
| 4. API Threshold Alerts | 5/5 · Cron, 30 lines | 4/5 · Cron, don't touch memory core | 5/5 · Low cost, high value | **HIGH** — Put in cron. 3 thresholds: <$5 ⚠️, <$1 🚨, $0 ❌. |
| 5. USER.md Cleanup | 5/5 · Consolidate 9→6 rules | 5/5 · Move behavioral rules to MEMORY.md | 4/5 · Restructure content boundary | **HIGH** — Immediate content cleanup. Behavioral rules belong in MEMORY.md, not USER.md. |
| 6. Trailing Metadata | 5/5 · Delete | 5/5 · "别犹豫，删" | 5/5 · 5-min fix | **UNANIMOUS** — Zero controversy. 376-char changelog has zero operational value. |

## Key Insights Per Model

### DeepSeek V4 Pro: Three-Layer Cascade Dependency

The 6 issues form a hierarchy:
1. **Routing layer** (Issue 2) — Top-level architectural debt. Without domain-based routing, all char-limit expansions are palliative — 5 semantic domains mixed in one flat pool erodes prompt utilization.
2. **Consistency layer** (Issues 1+3+5) — Mid-level operational debt. Three time-window fractures: post-write invisible (Issue 1), write-time unvalidated (Issue 3), write-space unplanned (Issue 5).
3. **Observability layer** (Issues 4+6) — Outer operational debt.

**Unique recommendation:** "Live memory delta" — maintain a `_post_snapshot_additions` list in memory tool. Each add() appends a content summary. `format_for_system_prompt()` returns frozen snapshot + delta suffix. Snapshot stays byte-stable (prefix cache warm), but model sees recent changes.

### MiMo V2.5 Pro: Cost-to-Value Analysis

**Must-do immediately (< 2 hours):**
1. Delete trailing MEMORY.md metadata (30 seconds)
2. Restructure USER.md content boundary (5 minutes — move behavioral rules to MEMORY.md)
3. Auto-trigger mid-session reload on add/replace (1 hour)

**This sprint (1-2 days):**
4. Memory Routing Phase 1 — section params + list_sections
5. add() non-blocking warnings

**Can wait:**
6. Memory Routing Phase 2 — double-delimiter parsing
7. API alerts — put in cron, not urgent

**Key insight:** USER.md currently stores content that belongs in MEMORY.md — behavioral rules (9 items, ~880 chars) are agent directives, not user identity. Re-draw the boundary: USER.md answers "who is the user", MEMORY.md answers "what the agent should know/do".

### Codex GPT 5.5: Industry Practices

**Validates the frozen-snapshot design** as the right call — most frameworks (LangChain, AutoGPT) fail to do this, causing prefix cache thrashing.

**On semantic conflict detection:** "An unsolved problem in production-grade agents. Mem0, Supermemory, LangChain, CrewAI all have no reliable implementation. False positives destroy trust more than missed contradictions."

**References found:**
- LangChain: `ConversationSummaryBufferMemory` — sliding window by token threshold + summary compression
- Mem0: Automatic dedup via vector similarity > 0.92 threshold
- Claude Code: No `/reload` command; uses `/compact` to force refresh
- Cursor: `.cursor/rules/*.mdc` directory — one file per domain
- AutoGPT: JSONL memory with id/timestamp/source per entry
- Letta (MemGPT): Core memory (always in context) + archival memory (evicted when over window)

## Web Search Findings

### Hermes Already Has 6-Layer Hallucination Defense

The existing codebase (`memory_tool.py`) already implements:

| Layer | Mechanism | Location |
|-------|-----------|----------|
| 1. Write Filter | `_scan_memory_content()` — 32 threat patterns, strict scope | `add()/replace()` |
| 2. Load Filter | `_sanitize_entries_for_snapshot()` — secondary scan at snapshot build | `load_from_disk()` |
| 3. Snapshot Isolation | Frozen `_system_prompt_snapshot` prevents mid-session injection | `build_system_prompt_parts()` |
| 4. Dedup | `dict.fromkeys()` on load | `load_from_disk()` |
| 5. Drift Detection | Round-trip mismatch + entry-size overflow checks | `_detect_external_drift()` |
| 6. File Lock | `fcntl.flock()` + atomic write | `_save_target()` |

### Available But Unused: External Memory Providers

Hermes ships with plugins but they aren't enabled by default:

| Provider | Key Capability | Enable Command |
|----------|---------------|----------------|
| **mem0** | Source-anchored memory, triple-layer (extract→integrate→retrieve), HaluMem-evaluated | `hermes provider memory mem0` |
| **hindsight (Vectorize)** | Reflective memory — extract after task completion, not during. 94.6% on LongMemEval | `hermes provider memory hindsight` |
| **honcho** | Cross-agent, cross-user memory management | `hermes provider memory honcho` |
| **supermemory** | Third-party provider | `hermes provider memory supermemory` |

### Academic Research

| Paper | Key Idea | Relevance |
|-------|----------|-----------|
| **HaluMem** (arXiv 2511.03506) | First operational-level memory hallucination benchmark. Three tasks: extraction, updating, QA. 50%+ failure rate on existing systems. | **High** — Could evaluate Hermes memory |
| **Eywa** (arXiv 2605.30771) | "Evidence before belief" — immutable evidence layer + derived belief layer. 88.2% on LongMemEval-S. | **High** — Source anchoring pattern |
| **A-MEM** (arXiv 2502.12110) | Zettelkasten-style cards with explicit links between memories | **Medium** — Structured memory linking |
| **Schema-Grounded Memory** (arXiv 2604.27906) | Define memory schema → extract facts into schema → resolve conflicts by timestamp | **Medium** — Lightweight schema for MEMORY.md |

## Roadmap: Phase 0-3 Execution Plan

### Phase 0 — Quick Fixes (< 2 hours, zero architectural risk)

| Step | Estimate | Value |
|------|----------|-------|
| P0-1: Delete trailing MEMORY.md metadata (376 chars) | 30 sec | Reclaims 376 chars/session |
| P0-2: Clean USER.md — consolidate 9→6 behavioral rules, move directives to MEMORY.md | 10 min | Reclaims ~300 chars, fixes content boundary |
| P0-3: Add balance thresholds to `daily_api_summary.py` (< $5 🔴, < $1 🚨) | 30 min | Prevents surprise API exhaustion |

### Phase 1 — Write-Time Consistency (Half day)

| Step | Estimate | Value |
|------|----------|-------|
| P1-1: `add()` gets non-blocking conflict detection — reuse `detect_contradictions()` from memory_review.py | 1 hr | Catches conflicts at write time without breaking workflow |
| P1-2: Add "Recent additions this session" volatile suffix — incremental delta, no snapshot rebuild | 1 hr | Model sees new memory mid-session, prefix cache stays warm |

### Phase 2 — Architecture Upgrade (2-3 days)

| Step | Estimate |
|------|----------|
| P2-1: Memory Routing Phase 1 — section params + list_sections action | 1 day |
| P2-2: Memory Routing Phase 2 — `_read_file()` double-delimiter parsing (§ + ##), domain-aware conditional injection | 2 days |

Faster alternative: enable `mem0` external provider for immediate vector indexing + source anchoring.

### Phase 3 — Ongoing Operations (Weekly)

| Step | Frequency |
|------|-----------|
| Push `memory_review.py` results to Feishu automatically | Weekly |
| Alert when capacity < 4 weeks remaining | Weekly |
| Evaluate enabling external memory provider (mem0/hindsight) | Once |
