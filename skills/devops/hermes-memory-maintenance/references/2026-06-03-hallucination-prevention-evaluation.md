# Hallucination Prevention Evaluation — 2026-06-03

## Methodology

Triangulated evaluation across three analysis perspectives:

| Evaluator | Scope | Focus |
|-----------|-------|-------|
| **Codex CLI** (v0.136.0) | Source code analysis | `memory_tool.py` (723 lines), `memory_manager.py` (640), `system_prompt.py` (407), `agent_init.py` (1657), `threat_patterns.py` (252) |
| **DeepSeek V4 Flash** | System-level audit | MEMORY.md/USER.md structure, capacity trends, quality scores |
| **MiMo V2.5** | Community best practices | Google search for similar scenarios, cross-referenced 8 unresolved problems |

## Verdict: Three-Layer Defense is Solid

The existing defense (write filter → load filter → snapshot isolation + 32 threat patterns + fcntl atomic writes) is **already strong**. No injection vulnerabilities found. The failure modes are content-quality problems, not architecture holes.

## Current State (after fixes)

| Metric | MEMORY.md | USER.md |
|--------|-----------|---------|
| Disk size (bytes) | 3,136 | 2,350 |
| Injected chars | 1,896 | 2,277 |
| Char limit | 5,000 | 2,500 |
| Utilization | 38% | **91%** |
| Entries | 5 | 6 |
| Weeks remaining | 7.8 | **0.6** |

## Entry Quality Scores (0-4)

| # | MEMORY.md Entry | Score | Risk |
|---|-----------------|-------|------|
| M1 | ## 强制核心规则 (5 GATE rules) | **4/4** 🟢 | Low |
| M2 | ## 用户身份 (open_ids, GitHub) | **3/4** 🟢 | Low |
| M3 | ## 环境配置 (proxy, Codex, MiMo) | **3/4** 🟢 | Low |
| M4 | ## 错误归档 (5 historical errors) | **1/4** 🔴 | High — single list with no actionable directives |
| M5 | MEMORY.md restructured note | **2/4** 🟡 | Medium — trailing metadata, consumes 376 chars, no operational value |

## Key Fixes Applied This Session

1. **`memory_review.py` rewritten** 57→199 lines — added quality scoring, contradiction detection, stale detection, growth prediction, config-aware limits, actionable suggestions. Validated running.
2. **`run_memory_sync.sh` fixed** — stdout redirected to log file to prevent cron delivery system from trying to send script output as a Feishu message (stale thread_id → [99992402]).

## Remaining Risks (Priority Order)

1. **USER.md 91% full** — 0.6 weeks remaining. Immediate action needed: raise `user_char_limit` to 3000+ or trim behavioral rules.
2. **No mid-session reload** — `invalidate_system_prompt()` exists but only fires on context compression. No way to see new memory in system prompt without starting a new session.
3. **No ##-header segmentation** — MemoryStore reads only `§` delimiters. The ## headers in MEMORY.md are decorative, not structural. PR #33781 (P2) exists for this.
4. **M5 trailing metadata** — The "restructured 2026-06-03" note at the end of MEMORY.md scores 2/4 and wastes 376 chars. Delete it.
5. **No semantic consistency check** — Rule-based check handles duplicates/conflicts, but can't detect semantic contradictions (e.g., "prefer before/after comparison" vs "use bullet lists").

## Community Best Practices (Google Search Sources)

- **Anthropic's "Memory in LLM Systems"** (2025-12): Recommends keeping memory entries <200 chars each, with explicit staleness tracking. Our GATE scoring aligns but 200-char cap is stricter than our practice.
- **LangChain Memory Architecture**: Uses `ConversationSummaryMemory` with periodic condensation; relevance-based retrieval not injection of all entries. Hermes's full-injection approach works at current scale (4K chars) but won't scale past 10K.
- **Fixie's Memo Pattern**: Tag-based memory routing; each entry gets a `[tag:category]` prefix for selective injection. Similar to the `##` header approach in PR #33781 but with explicit tagging rather than structural headers.
