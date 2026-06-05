# Error Pattern Audit — 2026-06-03

Source: Self-audit requested by Duruo after observing "最近幻觉和出错很严重."

## Pattern 1: Verify-Before-Assert Violations

| Instance | What the agent said | Truth | Root cause |
|----------|-------------------|-------|------------|
| Hermes Desktop | Said no desktop version exists | apps/desktop/ exists in repo, Electron app shipping | Checked local pip install only; didn't check GitHub repo |
| FEISHU_APP_ID | Said "你的 .env 里没有配这两项" | Both ID and secret were set in ~/.hermes/.env | Didn't grep the file before speaking |
| Group sender | Assumed a group message was from Duruo when it was from Raya | Raya's open_id in the message payload | Didn't re-check sender metadata |
| GitHub Token | Asked "GitHub 认证了没有?" twice after user already shared token | Token in .env AND used to file Issues/query PRs | Didn't read memory before asking user |

**Fix:** Three-step check rule (see skill Core Principle). For credentials: read memory first, check files second, ask user last.

## Pattern 2: Execute-Before-Read Violations

| Instance | What happened | Fix |
|----------|--------------|-----|
| Kanban update | User sent a long message with content + request. Agent ran Kanban command and reported output. User: "这个消息你没回." | Read full message first, acknowledge, then execute. |
| MiMo output hidden | User asked agent to call MiMo for discussion. Agent used `terminal` to call MiMo — output went to agent's context, not user's visible message. User: "什么都没显示给我呢." | After any tool call that produces user-facing content, present the output in your response. terminal/stdout results are invisible to the user by default. |

**Fix:** Read-before-executing protocol. After tool calls, always surface results visibly.

## Pattern 3: Session Re-Entry Identity Errors

| Instance | What happened | Root cause |
|----------|--------------|------------|
| Duruo/Raya confusion | After session expired, agent summarized Duruo's topics (skill audit, GitHub Issues) to Raya as "we talked about" | Didn't check who was talking; grabbed last session's summary |

**Fix:** Session re-entry protocol (see skill Core Principle).

## Pattern 4: Third-Party Model Fabrication

| Instance | What happened | Root cause |
|----------|--------------|------------|
| "xiaomei" | MiMo model used placeholder name "xiaomei" for Raya. Agent repeated it without cross-checking. | Trusted external model output over stored identity data |

**Fix:** Always cross-check names from external models against USER.md/MEMORY.md. Discard mismatches.

## Pattern 5: Memory Duplication Dilution

Repeated instructions across multiple memory entries dilute their effectiveness. For example:
- "先查官方来源" appears in MEMORY.md entries 21 and 25 AND USER.md entry 34 — three copies of the same rule
- Codex-related entries (mode switching, auth.json, proxy prefix) spread across entries 1, 13-14, 15-16, 17

**Fix:** Keep one canonical version per rule. Consolidate related entries.

## Remediation Status

- [2026-06-03] Verify-before-assert rule added to skill Core Principle
- [2026-06-03] Read-before-execute rule added to skill Core Principle
- [2026-06-03] Session re-entry protocol added to skill Core Principle
- [2026-06-03] Multi-model debate reference added to harness-engineering skill
- [2026-06-03] Memory-first credential check added to verify-system-state skill
- [ ] Memory consolidation still pending (MEMORY.md still has duplicates)

## Pattern 6: Premise Fabrication → Pipeline Amplification (2026-06-03)

| Instance | What happened | Root cause |
|----------|--------------|------------|
| Skill example → multi-model pipeline | Agent read `[user:duro]`/`[user:raya]` tone blocks from this skill's Problem 1 examples, treated them as user-confirmed facts, then delegated to MiMo + DS Pro for analysis based on that false premise. Both models produced lengthy evaluations of a non-existent problem. | No premise verification step in delegation pipeline. Skill example content indistinguishable from user-confirmed facts. |
| "Raya would feel cold" | Agent further deduced that Duruo's assumed tone would feel cold to Raya — a second-order inference built on the already-fabricated premise. | No "ask the user" step before asserting tone preferences. |

**Fix:**
1. Add premise verification as a mandatory step in delegation pipeline
2. Never treat skill example/template blocks as user facts — check actual memory files
3. Before asserting any user preference, ask the user

## Pattern 7: Unauthorized Upstream GitHub Operations (2026-06-03)

| Instance | What happened | Root cause |
|----------|--------------|------------|
| 5 PRs to NousResearch/hermes-agent | Agent independently created 5 PRs, including one that deleted upstream CI workflow files (-2389 lines). | No approval gate for git push/delete/force. |

**Fix:**
1. MEMORY.md rule 8 — GitHub operations require explicit user confirmation
2. Never push/delete/force upstream branches without asking
