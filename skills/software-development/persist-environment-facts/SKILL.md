---
name: persist-environment-facts
description: >
  "Use when: installing system tools (apt/pip/npm/git clone/cargo), modifying Hermes config, discovering environment facts (paths, installed tools, tool quirks), or after a user corrects you about something you should have remembered. Ensures durable environment state is systematically saved to persistent memory."
version: "1.0.0"
compatibility: Hermes Agent
metadata:
  hermes:
    tags: [hermes, environment, facts, persistence, setup]
    related_skills: [skill-maintenance-audit, verify-system-state]
    trigger: manual
---

# Persist Environment Facts

Meta-cognitive discipline: **systematically persist durable environment facts to agent memory so future sessions don't need to rediscover them.**

## When to use

Activate this skill whenever you:
- Install or configure a system tool (apt, pip, npm, git clone, cargo install, go install, etc.)
- Make any environment mutation that a future session would benefit from knowing about
- Are corrected by the user about something you should have remembered

Run through the steps below **in the same response** as the mutation or correction.

## Steps

### 1. Immediate persistence after any environment mutation

Call `memory(action='add', target='memory', content='...')` immediately. The entry must contain:

- **What** — package name, tool name, version if known
- **How** — install method / command used
- **Where** — binary path, config path, port number
- **Why** — purpose, what task it supports
- **Config specifics** — language packs, flags, non-default settings

Good example:
```
NUC 已安装 tesseract-ocr（中英文）+ pytesseract，路径 /usr/bin/tesseract。
用于截图文字 OCR，免费本地方案。配了 chi_sim 中文语言包。
```

### 2. Before reinventing, check what already exists

When asked to do something that might have existing tooling:

1. **Check memory first** — the memory block at the top of your prompt is checked every session. If a tool was saved, you'll see it.
2. **If memory is silent, session_search** — search for past installs, configs, or attempts
3. **Only then decide** — reuse existing tool if found. Build a new solution only if genuinely needed (existing tool can't do the job, or the task is fundamentally different).

### 3. After user correction about a forgotten fact

If the user says "this was already installed / already done / I told you this before":

1. Acknowledge the correction
2. **Immediately save to memory** — do NOT just session_search and move on
3. If memory is over 85% full (check the returned `usage` field), consolidate or trim before adding

### 3b. Verify tool still exists before using it

Memory says a tool is installed, but the binary might have been removed between sessions (apt auto-clean, system updates). Before defaulting to memory's word:

1. Check if the binary still exists: `which <tool>` or `test -f <path>`
2. If missing but the Python library is still installed (e.g. tesserocr without the binary), document the alternative
3. If truly gone, reinstall or pivot — don't assume memory is current

When recording a tool path in memory, note whether it depends on a system binary (can disappear) or a pip package (more stable). Prefer pip-based setups on headless/no-sudo hosts.

### 3c. Source .env before checking environment variables

Credentials and tokens are often stored in `~/.hermes/.env` (format: `export VAR=value`), not as live environment variables. `echo "${#VAR}"` returns 0 for vars in .env that haven't been sourced.

Before reporting "variable not found":
1. Check `source ~/.hermes/.env 2>/dev/null` first, then re-check the variable
2. If still missing, check `grep "VAR" ~/.hermes/.env` — it might exist but not be exported
3. Only then conclude the token/credential is truly absent

**Read token from .env in scripts** (preferred): parse the file directly with `re.match(r'^(?:export\s+)?VAR\s*=\s*(.+?)\s*$', line)` rather than relying on environment inheritance.

### 4. Memory vs. Skills: what goes where

This is the **most critical distinction** for memory capacity management. Violating it is the #1 cause of memory overflow.

| Goes in **memory** (dynamic, changeable) | Goes in **skills** (static, procedural) |
|---|---|
| User preferences, habits, pet peeves | How to install X, debug Y, or do Z |
| Environment state (what's installed, what paths) | CLI command syntax, API endpoint docs |
| Current running services, active cron jobs | Tool usage patterns, coding conventions |
| Network topology, hostnames, IPs | Framework setup steps, deployment playbooks |
| Hardware specs, timezone, locale | Feature comparisons, architecture decisions |
| Persona info (names, roles, relationships) | Skill format specs (agentskills.io schema) |

**Why this matters:** Static knowledge (skill format specs, CLI arguments, API docs) can be 200-400 chars per entry. When 10 such entries pile up in 2,200-char memory, they crowd out real preferences and environment facts — the things that actually change between sessions and that you can't recover from skills or docs.

**The litmus test:** If tomorrow the fact will still be true and you could have looked it up from a doc or a skill, it probably belongs in a skill.

### 5. Manage memory capacity (the consolidation pattern)

Default 'memory' target limit: ~2200 chars (configurable via `memory.memory_char_limit`). Keep entries lean:

- One sentence per fact, ~60-120 chars each — shorter is better
- Use `§` separator between entries (existing convention)
- **Avoid redundancy** — don't put the same fact in both MEMORY.md and USER.md. If a fact applies to both "who the user is" and "how the system works", pick one target. Example: girlfriend open_id → memory, not user. User's complaint about format → user, not memory.
- **Consolidate related facts into one entry** — e.g. merge "Codex CLI at /path" + "Claude Code at /path" into one line
- **Prune periodically:** stale cron job IDs, fixed workarounds, resolved preferences that became conventions
- **Expand the limit** if you consistently run out despite good hygiene — `hermes config set memory.memory_char_limit 5000`. At ~1,800 tokens of injected context at 5K chars, this is noise-level compared to a typical model call (~5K-10K+ tokens).  **Default recommended minimum: 5000.** The default 2200 fills up in ~2-3 days of moderate use, and overflow causes silent data loss (new entries rejected, existing entries truncated mid-injection into system prompt).

**When memory hits >85% (check the `usage` field in `memory()` response):**

1. First, consolidate — look for redundant entries across both memory stores (MEMORY.md + USER.md), merge duplicates
2. Second, purge static knowledge — anything that's really a skill (API format, tool usage, setup steps) should be moved to a skill
3. Third, expand the limit if consolidation only buys a small margin
4. Only then start removing genuinely useful dynamic facts

### 6. Verify persistence

After `memory(action='add', ...)`, check the `usage` field in the response:
- `"usage": "100% — X/Y chars"` → entry was truncated or not saved. Prune first, re-add.
- `"usage": "X% — N/Y chars"` with N growing → success.

### 7. Pre-interruption persistence (save BEFORE process-killing operations)

**Scenario:** You are about to do something that will kill or interrupt your own process — gateway restart (`hermes gateway restart` from terminal), gateway drain, sending `/restart`, session context compression, or any operation you know will destroy your current agent context.

**Critical rule: Save memory BEFORE you trigger the kill, not after.** Once the process is killed, no tool call can execute.

#### Step-by-step protocol

1. **Identify** — Do you know this action will destroy your context? If yes → proceed. If unsure, assume it might.
2. **Collect** — What observations from this session should persist? User preferences, environment facts, config changes, analysis results.
3. **Save** — Call `memory(action='add', ...)` immediately. The write is synchronous and uses `atomic_replace` (writes to a temp file first, then renames atomically). This IS durable.
4. **Verify** — Read MEMORY.md back by calling `memory(action='read', ...)` or `read_file(~/.hermes/memories/MEMORY.md, offset=1, limit=10)`. Confirm your entry is visible.
5. **Only then** — Trigger the process-killing operation.

#### What gets lost and why

When the gateway restarts (via `hermes gateway restart` in terminal or `/restart` in Feishu):

- **Your current session context** is fully destroyed — new agent, new session, no memory of what was happening
- **In-flight background reviews** (the "Self-improvement review: Memory updated" thread) are killed mid-execution. Even though the review fork calls the same `memory tool`, if the parent is killed before the fork's write completes (atomic rename finishes), the write is lost.
- **The MEMORY.md file on disk survives** — it's just a flat file. If a prior `memory()` call completed before the restart, the data IS there. The problem is operations that happen *after* the last `memory()` call but *before* the restart finishes.

**Root cause chain:**
```
You ask me to restart gateway
  → I call terminal("hermes gateway restart")
  → Gateway sends SIGUSR1 to its own process
  → Gateway drain infrastructure starts killing agents (180s timeout)
  → My terminal subprocess is killed → no return value
  → My agent is interrupted and killed
  → Any tool output since last memory write is gone
  → New gateway starts → brand new agent → no recollection
```

**Pattern that avoids this:**
```
I need to restart gateway
  → I save memory FIRST (memory tool, synchronous, persistent)
  → I verify the write (read MEMORY.md back)
  → I trigger restart (via /restart in Feishu, or user SSH)
  → New agent starts → reads MEMORY.md → knows what happened
```

#### Debounce: only restart when truly needed

Before triggering a gateway restart, ask:

- Does this change require a restart? (Some config changes hot-reload; others don't.)
- Can the user trigger the restart later? (If it's not urgent, let them decide.)
- Can I use a simpler reload mechanism? (Some platforms support `/restart` which is cleaner than `hermes gateway restart`.)

**Changes that DO need restart:** platform credentials, provider config, memory provider switch, platform enable/disable.
**Changes that OFTEN don't:** visual model config, auxiliary model config (check the platform's hot-reload support first).

#### The upstream gap: pre-drain checkpoint hook

Hermes gateway has **no mechanism** to ask an active agent "save your state before I kill you." The drain process (`gateway/restart.py`, 180s timeout) starts killing agents immediately. There's no `on_shutdown(save_state=True)` hook.

This means the **only** defense is proactive: save before you trigger the kill. An upstream PR to add a graceful shutdown hook would provide a safety net for cases where the agent can't save preemptively (e.g., user requests restart while the agent is mid-tool-call).

**Upstream feature sketch:**
```python
# In gateway/run.py restart_signal_handler()
# Before draining agents, emit a "checkpoint" signal
# Each active agent calls memory tool for final sync
# After all agents complete (or timeout), proceed with drain
```

#### External memory providers as safety net

Flat-file memory (`MEMORY.md`) uses atomic writes which are robust, but if the agent is killed between writes, the in-between observations are lost. Database-backed memory providers offer stronger guarantees:

| Provider | Persistence Model | Survives Restart? | Setup |
|----------|------------------|-------------------|-------|
| **Built-in** (flat file) | atomic_replace, single file | ✅ if write completed | Default, no setup |
| **Honcho** | SQLite/PostgreSQL, transactions | ✅ every write atomic | `hermes memory setup` |
| **Mem0** | Vector DB, indexed writes | ✅ every write durable | `hermes memory setup` |
| **OpenViking** | Virtual filesystem via `brv` CLI | ✅ depends on backend | Install `brv` CLI |

Database-backed providers won't help if the observation was never sent (the agent was killed before calling the write). But they 100% prevent the "write was in progress and got killed" scenario — transactions are atomic.

#### Pitfalls

- **Don't try to "restart and hope for the best".** If you didn't save, the restart WILL lose your context. There is no recovery.
- **Don't trigger gateway restart from terminal** (`hermes gateway restart`). You kill yourself and get no return value. Use `/restart` in the chat instead — but even then, save memory FIRST.
- **Don't assume background reviews will save for you.** The background review fork runs asynchronously. If the parent is killed before the fork's atomic write completes, the "Memory updated" message was misleading — the write may not have landed.
- **Session_search is recovery, not prevention.** After restart, you can `session_search(query='...')` to find what the previous session was about. But memory is cleaner and faster.
- **Verify doesn't mean assume.** Read the file back. `memory()` returning "success" doesn't guarantee the next session will see it — but `read_file` confirming the entry on disk is as close to certain as you can get.

### 8. Periodic memory auto-review (cron pattern)

To prevent memory drift and overflow proactively, consider a recurring cron job that audits memory content:

**When:** Weekly (e.g., Sunday 03:00)

**What it does:**
1. Reads MEMORY.md and USER.md
2. Scans for redundancy (facts appearing in both files, or repeated in different entries)
3. Flags stale entries (facts about services/scripts/cron jobs that may have changed)
4. Suggests skill-worthy content (stable procedures that should move to a skill)
5. Outputs a report — the agent then decides whether to consolidate

**Do NOT** let the cron job directly write to memory — it should only analyze and report. Direct writes skip user approval and can accidentally delete important context.

**Implementation sketch:**
```
cronjob(
  action='create',
  schedule='0 3 * * 1',  # Monday 03:00 local time
  prompt='Read ~/.hermes/memories/MEMORY.md and ~/.hermes/memories/USER.md. Identify redundancy, staleness, and content better suited as skills. Output a brief report with specific recommendations.',
  skills=['persist-environment-facts'],
  enabled_toolsets=['file'],
)
```

**Pitfall — cron timezone:** The scheduler interprets cron expressions in the system's local timezone (CST/Asia/Shanghai on this NUC). `0 19 * * 0` means Sunday 19:00 CST, **not** Monday 03:00 CST. To run Monday 03:00, use `0 3 * * 1`.

**Pitfall — cron session self-restriction:** The cron agent must have `skip_memory=True` (default) so it doesn't inject the same memory it's trying to audit. Give it `enabled_toolsets=['file']` — it only needs to read the memory files, not use any interactive tools.

### 8. Route user commands through the correct tool

When memory records a user preference about which tool to use for a task (e.g., "screenshot OCR → tesseract, not MiMo"), the entry is an **invariant routing rule**. Future sessions must respect it without re-evaluating.

Pattern for such entries:
```
<task trigger>: <what to use>, not <what not to use>. Reason: <why>.
```

Example from live memory:
```
图片识别路由：用户说"截图读文本"或"读取文字"→调tesseract(终端)。否则默认用MiMo/vision_analyze。不要所有图片截屏都走MiMo，纯文字优先用本地tesseract。
```

These routing rules act as a lightweight preference layer on top of the tool system. They should be:
- **Short** (1-2 lines) so they fit in the memory-limited system prompt
- **Actionable** — the agent knows exactly which tool to call
- **Contextual** — include the trigger condition

## Pitfalls

- **session_search is NOT a substitute for memory.** Sessions age out of the DB. Memory persists indefinitely. If a fact matters later, it MUST go to memory.
- **Don't treat install commands as transient task state.** System tool installs are durable environment changes. They belong in memory.
- **Don't skip saving because memory is near capacity.** Prune instead.
- **Don't save negative tool claims** ("browser tool doesn't work"). Save the FIX instead.
- **Don't save session narratives** ("fixed bug X in session Y"). Use session_search for recall.

## Verification

After saving, the fact should appear in the memory block at the top of every subsequent session's prompt. If it's missing, the write failed — check MEMORY.md file permissions at `~/.hermes/memories/MEMORY.md`.

## Reference Materials

- `references/memory-consolidation-patterns.md` — concrete consolidation example with before/after char counts, anti-pattern catalog, and the expand-vs-consolidate decision tree.
