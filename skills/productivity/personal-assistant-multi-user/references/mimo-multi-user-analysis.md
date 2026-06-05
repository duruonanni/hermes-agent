# MiMo v2.5 Pro Multi-User Analysis

Analysis from 2026-06-02 session. MiMo model (mimo-v2.5-pro) was asked to evaluate 7 multi-user issues on a shared Hermes Agent instance.

## Priority Matrix

1. **🔴 Memory conflict** — Two users have opposite tone/format preferences. MEMORY.md/USER.md is global. Solution: USER.md segmentation with `[user:xxx]` markers + runtime sender check.
2. **🔴 Approval blocking in group chat** — Approval prompts embed a button in the last message card. Group chat users can't see the button → session blocks permanently. Solution: platform-aware approval (DM: normal, group: auto-reject with redirect).
3. **🔴 Context cross-contamination** — Even with group_sessions_per_user=true, agent references other users' history. Solution: metadata-first context filtering rule.
4. **🟡 Identity confusion** — Agent knows both open_ids but still guesses sender from text content. Solution: always check event.sender.open_id, never infer from text.
5. **🟡 Skill role filtering** — Admin skills load for all users. Solution: tag-based filtering.
6. **🟢 Cost contention** — Two users share one API key. Solution: usage logging first, quota later.
7. **🟢 Cron report routing** — All reports go to primary user. Solution: per-job `deliver` target + subscriber concept.

## Implementation Phases

### Phase 1 — Stop the Bleeding
- Group chat approval: skip/auto-reject in group, 60s timeout fallback
- USER.md segmentation
- Identity: metadata-first prompt rule

### Phase 2 — Experience Improvement
- Context view isolation (filter history by sender)
- Skill permission tags

### Phase 3 — Long Term
- Token usage tracking
- Report subscription system

## Key Warnings from MiMo

- Do NOT try to split into two Hermes instances (resource overhead)
- Do NOT modify Hermes core code if avoidable — all changes in config/prompt layer
- Identity resolution must be checked EVERY turn, not just at setup time
- **[CRITICAL] MiMo may fabricate names.** In its initial analysis, MiMo invented "xiaomei" as a placeholder for the secondary user. This hallucinated name was propagated into skills before being caught. When using MiMo (or any model) for design consultation, always verify every name/label it suggests against actual stored user identities before committing it to any file.
