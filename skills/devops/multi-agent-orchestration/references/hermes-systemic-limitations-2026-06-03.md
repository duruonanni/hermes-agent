# Hermes Systemic Limitations — 2026-06-03

Audit performed after user asked "why is this so chaotic" following a chain-hallucination incident that consumed 3 agent turns and 2 subagent analyses before discovery.

## The 5 Structural Problems

### Problem 1: Skill Provenance Blind Spot (P0)
Agent-created skill content and user-confirmed knowledge live in the same file format, in the same filesystem, with zero distinguishing markers at runtime. When an agent session writes a template example into a skill (e.g., `[user:duro] 语言风格：简洁务实`), a future session reads that skill and treats the example as authoritatively as it treats user-verified facts like `SearXNG port: 8888`.

**Community tracking: 0 issues.** No known work exists for skill content provenance in the Hermes community.

**Fix path:** Skill template sections must carry visual markers (WARNING blocks, provenance notes) that the agent can scan. The agent must have a runtime rule: "if a claim came from a skill code block/indented template, flag it as unconfirmed."

---

### Problem 2: Rules Are Prompt Engineering, Not Constraints (P2)
MEMORY.md rules 1-8 look hard but are pure text. The agent can choose to comply or not — no compiler, no runtime, no type system enforces them. Every rule is self-policed by the same system that needs policing.

**Community tracking:** Partial. #33143 (global rules file) and #31562 (cross-profile SHARED.md) propose similar ideas but both P3 with no ETA.

**Fix path:** Accept the limitation. Rules work *most* of the time for simple patterns. Complex multi-step guardrails need programmatic enforcement (plugin hooks, tool-level gates). The Premise Gate pattern (see pipeline-error-amplification.md) is a manual approximation.

---

### Problem 3: Cross-Session Amnesia (P1)
Each new session starts with a fresh MEMORY.md snapshot. Previous session errors have zero weight. A hallucination documented at 19:00 can be repeated at 19:30 by a different agent session loading the same files. The system doesn't learn from its mistakes across sessions.

**Community tracking:** Active. #26045 (memory drift, P0, CLOSED) fixed tool-level overwrite. #22612 (memory routing, P3, OPEN) proposes indexed sub-documents but has no ETA.

**Fix path:** Cron-based lessons-learned extraction (`memories/lessons.json`), plus explicit WARNING blocks in skill files that describe known failure modes. The agent must scan for these blocks before consuming skill content.

---

### Problem 4: Pipeline Error Amplification (P1)
When the orchestrator correctly executes the multi-agent pipeline (load skill → delegate to MiMo → delegate to DS Pro → aggregate), but the initial premise is wrong, the pipeline magnifies the error 2-3×. Each subagent receives the false premise in its context, produces confident analysis on it, and the final summary treats the agreement across models as validation.

**Community tracking: 0 issues.** This is a Duruo-specific pattern (multi-model chain evaluation). No community user has documented this failure mode.

**Fix path:** Premise Gate — before every `delegate_task`, strip or verify every factual claim in the context. Tag each claim with its source. If source is a skill template → strip. (See pipeline-error-amplification.md for full analysis.)

---

### Problem 5: Compression Signal Loss (P3)
When MEMORY.md/USER.md approach capacity, compression removes not just redundancy but also the context needed to distinguish real facts from agent-generated fiction. After compression, the note "this skill example was written by an agent" gets dropped before the note that's more useful for daily operations.

**Community tracking:** #37010 (pre-compression extraction, OPEN) has a code implementation but community disputes about the approach.

**Fix path:** Monitor capacity. Current MEMORY.md is ~4200/5000 chars (84%) and USER.md is ~2350/2500 chars (94%). At current growth rate, 2-3 months before compression triggers. When it does, use #37010's pattern: extract decision records to `memories/facts.json` before compressing.

---

## Interaction Matrix

| | Q1 Provenance | Q2 Soft Rules | Q3 Amnesia | Q4 Pipeline | Q5 Compression |
|---|---|---|---|---|---|
| **User's fault?** | No | No | No | No | No |
| **Community aware?** | No | Partial | Yes (#26045+) | No | Partial (#37010) |
| **Architecture limit?** | Yes | Yes | Yes | No | Yes |
| **Duruo can fix today?** | Yes | Workaround | Partial (cron) | Yes | Monitor |

## Key Insight

Problems 1 and 4 compound explosively: an unverified premise (Q1) fed into a multi-model pipeline (Q4) produces confident-sounding output indistinguishable from real analysis. This is the exact failure that triggered this audit.
