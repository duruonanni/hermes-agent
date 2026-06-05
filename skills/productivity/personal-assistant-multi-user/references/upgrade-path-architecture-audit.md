# Multi-User Memory Isolation: Architecture Audit (2026-06-03)

Evaluated by DeepSeek V4 Pro as "军师" (strategist) — architecture and long-term
maintainability perspective for the multi-user memory isolation scheme on Hermes Agent.

## Current Architecture State

### How Memory Gets Into the System Prompt

```
AIAgent.__init__()
  → MemoryStore.load_from_disk()
    → reads ~/.hermes/memories/MEMORY.md + USER.md
    → parses §-delimited or ##-headed entries via _split_by_sections()
    → runs _sanitize_entries_for_snapshot() (threat pattern scan)
    → captures _system_prompt_snapshot = {"memory": "...", "user": "..."}

build_system_prompt_parts() [system_prompt.py]
  → volatile_parts.append(agent._memory_store.format_for_system_prompt("memory"))
  → volatile_parts.append(agent._memory_store.format_for_system_prompt("user"))
  → volatile_parts.append(agent._memory_manager.build_system_prompt())  // external provider
```

### Frozen Snapshot Design

The MemoryStore has two parallel states:
- `_system_prompt_snapshot` — frozen at `load_from_disk()` time (agent init). Never mutated mid-session. Keeps prefix cache stable across all turns.
- `memory_entries` / `user_entries` — live state, mutated by memory tool calls, persisted to disk immediately.

`format_for_system_prompt()` returns the snapshot, NOT the live state. This means:
- Memory writes during a session persist to disk but do NOT appear in system prompt until NEXT session.
- The snapshot is byte-stable for the entire session, preserving provider-side KV cache.

### Gateway Routing (no per-user profile switching)

```
_handle_message(event)
  → pre_gateway_dispatch plugin hook (can skip/rewrite/allow)
  → _is_user_authorized(source)
  → session_store.get_or_create_session(source)
  → _handle_message_with_agent(event, source)
    → AIAgent(model=turn_route["model"], **turn_route["runtime"], ...)
      → (within run_sync() closure at gateway/run.py:12513)
```

**No code reads `event.target_profile` during agent creation.** The skeleton exists
in `_load_profile_routing()` + `_resolve_profile_for_user()` (gateway/run.py:3116-3142)
and sets `event.target_profile` on matched events (line 7098), but no downstream
code consumes it. Verified dead code as of v0.15.1.

### Relevant Plugin Hooks (hermes_cli/plugins.py:127-167)

Only `pre_llm_call` can modify the messages array before it reaches the LLM. Available hooks:

| Hook | Can change memory? | Limitation |
|------|-------------------|-----------|
| `pre_gateway_dispatch` | No (only skip/rewrite/allow) | Runs before agent exists |
| `on_session_start` | No (only event notification) | No memory access |
| `pre_llm_call` | ✅ Yes — modifies messages list | Breaks prefix cache |
| `pre_tool_call` | No (only block/allow tools) | Too late, memory already loaded |
| `transform_llm_output` | No (post-hoc text transform) | Too late |

## Key Architecture Risks

### 1. Frozen Snapshot vs pre_llm_call Conflict

The MemoryStore's frozen snapshot is designed for prefix cache stability. A Plugin
that swaps memory blocks at `pre_llm_call` time bypasses this freeze — every turn
mutates the system prompt, meaning the provider's KV cache (calculated from the
first N bytes of the system prompt) is invalidated on every turn.

**Cost:** ~2-5K extra tokens per LLM call (the prompt prefix up to the volatile
memory block). At 100 conversations/day × 3 turns each = 300 calls × 3.5K avg =
~1M wasted tokens/day ≈ $1-3/day.

### 2. External Memory Provider Blind Spot

```python
# system_prompt.py — both sources injected into volatile tier:
volatile_parts.append(mem_block)           # _memory_store
volatile_parts.append(user_block)          # _memory_store
volatile_parts.append(ext_mem_block)       # _memory_manager — NOT intercepted by Plugin
```

Any isolation that only intercepts `_memory_store` content (section-based or Plugin)
still leaks external provider content. To fully isolate, either:
- Disable external memory providers (`memory.provider: builtin` in config), or
- Also intercept/proxy the external provider at `MemoryManager.build_system_prompt()`.

### 3. Group Chat Cross-Contamination

The session_key derives from `chat_id + thread_id`, not from `sender.user_id`. In
certain edge cases (e.g., rapid sequential @mentions from different users in the same
group), the same agent instance can process User B's message with User A's memory
still loaded.

`group_sessions_per_user=True` helps at the transcript level but does NOT isolate
the loaded memory snapshot.

## Upgrade Path Cost Estimates

| Phase | Code change | Effort | Risk |
|-------|------------|--------|------|
| A→B (Plugin) | New `~/.hermes/plugins/memory-isolation/` | 2-4h | Low |
| B→C (Gateway routing) | ~50 lines in `gateway/run.py` + PR | 4-8h + merge wait | Medium |
| C→D (Multi-process) | Dockerfile + systemd units | 30min | Medium-high (resource cost) |

## Key File References (Hermes v0.15.1)

- `gateway/run.py:12513` — AIAgent creation in gateway dispatch
- `gateway/run.py:3116-3142` — `_load_profile_routing()` / `_resolve_profile_for_user()` (unused skeleton)
- `gateway/run.py:7306-7345` — `pre_gateway_dispatch` hook dispatch
- `agent/system_prompt.py:301-321` — volatile tier: both memory sources injected
- `tools/memory_tool.py:165-264` — MemoryStore class, load_from_disk, frozen snapshot
- `hermes_cli/plugins.py:127-167` — VALID_HOOKS set
