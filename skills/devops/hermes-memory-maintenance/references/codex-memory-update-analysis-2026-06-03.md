# Codex CLI: Memory File Update Principle Analysis

> Analyzed by Codex CLI on 2026-06-03  
> Source: `tools/memory_tool.py` (723 lines), `agent/agent_init.py`, `cron/scheduler.py`  
> Trigger: User expressed concern about MEMORY.md/USER.md being changed too frequently

## Key Findings

### 1. Update Principles (from code)

- **Frozen Snapshot**: System prompt memory is loaded once at session start, never mutated mid-session. Keeps prefix cache stable.
- **Immediate Persistence**: Every add/replace/remove writes to disk immediately via atomic `os.replace()`.
- **Separation**: MEMORY.md = environment facts; USER.md = user profile.
- **Char limits**: 5000/3000 chars for this user (configurable).
- **Threat scanning**: Write-time + load-time scanning with `strict` scope.
- **Priority**: User preferences/corrections > environment facts > procedural knowledge.

### 2. Who Writes to Memory Files

| Path | Writes? | Description |
|------|---------|-------------|
| `memory(action=add/replace/remove)` in session | ✅ Yes | Only actual write path |
| Cron: `weekly-memory-review` | ❌ No | Read-only analysis (`memory_review.py`) |
| Cron: `memory-feishu-daily-sync` | ❌ No | Reads files, syncs to Feishu doc |
| Cron: `weekly-skill-audit` | ❌ No | Skills audit only |
| Cron scheduler | ❌ No | Sets `skip_memory=True` for agent jobs |

### 3. Concurrent Write Safety

Three-layer protection:
1. `fcntl.flock` exclusive lock on `.lock` file
2. `_reload_target()` re-reads disk INSIDE lock (Session B sees A's writes)
3. Atomic write via tempfile + `os.replace()`

**Result**: Concurrent memory tool calls are serialized. No merge logic — drift detection rejects writes when external editing is detected.

### 4. Design Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| External tools bypass lock | 🔴 | Drift detection + .bak (reactive) |
| Frozen snapshot stale mid-session | 🟡 | Gateway mode creates new agent per message |
| No /reload memory command | 🟡 | Known issue (#10880, #17013) |
| Section separator collision | 🟢 | `\n§\n` format reduces false splits |
| Crash during atomic write | 🟢 | Very narrow window |

### 5. Recommendation

Enable hindsight/reflective memory (`hermes provider memory hindsight`) to batch-extract durable facts rather than writing per-interaction. In-session, aggregate related facts into one entry before writing.
