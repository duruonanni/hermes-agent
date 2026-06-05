---
name: cursor-cli
description: "Delegate coding to Cursor Agent CLI (features, PRs, automation) — subscription-based, no proxy needed from China."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Cursor, CLI, Automation, Headless]
    related_skills: [codex, claude-code, hermes-agent]
---

# Cursor Agent CLI — Hermes Orchestration Guide

Delegate coding tasks to [Cursor Agent CLI](https://cursor.com/cli) via the Hermes terminal. Cursor Agent CLI is Cursor's AI-powered coding agent that runs in terminal, GitHub Actions, and headless automation.

## When to Use

- Building features, refactoring, PR reviews
- One-shot coding tasks via headless print mode
- CI/CD automation pipelines
- **Preferred over Codex CLI when proxy is unreliable** — cursor.com is directly accessible from China without HTTPS_PROXY

## Prerequisites

- **Installed:** `curl https://cursor.com/install -fsS | bash` → installs to `~/.local/bin/agent`
- **Binary:** symlinked as `~/.local/bin/agent` and `~/.local/bin/cursor-agent`
- **Auth:** requires `CURSOR_API_KEY` env var (generate at cursor.com/settings) or `agent login` (browser OAuth)
- **Subscription:** CLI is included with Cursor Pro ($20/mo) and higher plans
- **Note:** CLI usage consumes the same premium request pool as the IDE subscription

### Connectivity Note (China)

cursor.com and api.cursor.com are directly reachable from mainland China — **no proxy needed**. This is a key advantage over Codex CLI (GPT-5.5 via chatgpt.com, requires HTTPS_PROXY).

```bash
# Test connectivity (both return HTTP/2 200)
curl -sI https://cursor.com
curl -sI https://api.cursor.com
```

## One-Shot Tasks (Headless / Print Mode)

The `--print` flag enables non-interactive mode — runs a task, outputs result to stdout, exits. Use this for most Hermes orchestration.

```bash
agent --print --model sonnet-4 "Add dark mode toggle to settings page"
```

### Common Patterns

```bash
# Quick task in project directory
agent --print "Fix the null check on line 42 in utils.ts" --workspace /path/to/project

# With API key env var
CURSOR_API_KEY=sk-... agent --print "Refactor auth module to use JWT"

# JSON output for parsing
agent --print --output-format json "List all functions in src/" --workspace /path/to/project

# YOLO mode (auto-approve all commands, including shell & write)
agent --print --yolo "Build a full API CRUD for users" --workspace /path/to/project

# Trust workspace in headless mode
agent --print --trust --yolo "Run tests and fix failures" --workspace /path/to/project

# Plan mode (read-only analysis, no edits)
agent --print --plan "Analyze the architecture of this project" --workspace /path/to/project

# Ask mode (Q&A, read-only)
agent --print --mode ask "How does authentication work?" --workspace /path/to/project
```

## Key CLI Flags

| Flag | Effect |
|------|--------|
| `--print` | Non-interactive one-shot mode (output to stdout, exits when done) |
| `--model <model>` | Model: `sonnet-4`, `gpt-5`, `sonnet-4-thinking`, etc. |
| `--output-format <fmt>` | Output format: `text`, `json`, `stream-json` |
| `--yolo` / `--force` | Auto-approve ALL commands (no prompts, fastest flow) |
| `--trust` | Trust workspace without prompting (headless only) |
| `--plan` | Plan mode — read-only, proposes plans, no edits |
| `--mode <mode>` | Start in `plan` or `ask` mode |
| `--sandbox <mode>` | `enabled` or `disabled` (overrides config) |
| `--approve-mcps` | Auto-approve MCP servers |
| `--workspace <path>` | Working directory |
| `--api-key <key>` | API key (alternative to CURSOR_API_KEY env var) |
| `--resume [chatId]` | Resume a session |
| `--continue` | Continue most recent session |
| `--list-models` | List available models for this account |

Available models (from `--list-models`) — depends on subscription tier. **Pro plan (tested):** `auto`, `composer-2.5`, `composer-2.5-fast` (default), `grok-build-0.1` (1M context), `grok-4.3` (1M), `kimi-k2.5`. Higher tiers (Pro+/Ultra) unlock Claude Sonnet 4, GPT-5, Gemini 2.5 Pro.

## Background Mode (Long Tasks)

```bash
# Start in background
terminal(command="agent --print --yolo --model sonnet-4 'Refactor the database layer' --workspace /project", background=true, timeout=300)

# Monitor (process tool)
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Delegation via Subagent

```python
delegate_task(
    goal="Add user authentication module with JWT tokens",
    toolsets=["terminal"],
    context="Use Cursor Agent CLI via terminal. "
            "Export CURSOR_API_KEY from .env or pass via --api-key. "
            "Run: agent --print --yolo --model sonnet-4 'Build JWT auth module' --workspace /project"
)
```

## Auth Methods

### Method 1: API Key (Headless/Scripting)

1. Go to cursor.com/settings → generate CURSOR_API_KEY
2. Set as environment variable: `export CURSOR_API_KEY=sk-...`
3. Or pass via `--api-key sk-...`

### Method 2: OAuth Login (Interactive)

```bash
agent login   # Opens browser for OAuth
```

Set `NO_OPEN_BROWSER=1` to get a URL instead of auto-opening (for headless servers).

### Method 3: Hybrid (Login on NUC, CLI uses stored token)

```bash
# On NUC (headless, set NO_OPEN_BROWSER)
NO_OPEN_BROWSER=1 agent login
# Copy the printed URL, open on your laptop, authenticate
# After success, CLI stores the token and works
```

### Check Auth Status

```bash
agent status
agent whoami   # Shows authenticated user info
agent models   # List available models
```

## Worker Mode (Private Cloud)

Cursor Agent can run as a **private worker** — an agent that connects to Cursor's cloud to execute tasks in your own environment:

```bash
agent worker start --api-key "$CURSOR_API_KEY"
```

This is useful for persistent background agents that process tasks from Cursor's job queue. Not needed for the primary headless/print-mode workflow.

## Comparison with Other Coding Agents

| | Codex CLI | Claude Code | Cursor CLI |
|---|---|---|---|
| Auth | ChatGPT OAuth | Anthropic OAuth / API key | CURSOR_API_KEY / OAuth |
| China connectivity | **Proxy needed** (chatgpt.com) | **Proxy needed** | **Direct ✅** (cursor.com) |
| Cost | GPT Plus sub + MiMo fallback | MiMo Token Plan + Claude Pro sub | **Your Cursor subscription** |
| Headless mode | `codex exec` ✅ | `claude -p` ✅ | `agent --print` ✅ |
| Model choice | GPT-5.5 only (or MiMo proxy) | Claude models | GPT-5, Sonnet-4, Gemini, etc. |
| MCP support | Deep | Deep | Limited (no MCP in CI/headless) |
| Git worktrees | Manual | Built-in (`--worktree`) | Built-in (`--worktree`) |

## Pitfalls & Gotchas

1. **Pro plan may not support CURSOR_API_KEY** — On Cursor Pro ($16-20/mo), the User API Key generated at cursor.com/settings returns "The provided API key is invalid" for CLI headless mode. This is a known limitation: API key support may require Pro+ ($48/mo) or Business plans. **Workaround:** Use OAuth login (`agent login` with `NO_OPEN_BROWSER=1`) for Pro. For headless automation on Pro, consider Codex CLI or Claude Code as fallbacks.

2. **API key required for headless** — `--print` mode needs `CURSOR_API_KEY` or `--api-key`. OAuth login alone doesn't work for CI/automation. But if API key is unavailable on Pro, headless automation is limited.
2. **No models available** without auth — `agent --list-models` returns nothing until authenticated.
3. **MCP not supported in headless/CI** — MCP approvals aren't implemented for `--print` mode in headless environments.
4. **CLI shares subscription quota** with IDE — heavy CLI usage may deplete premium requests faster than expected.
5. **Install updates manually** — `agent update` to get the latest version. Version is date-stamped (e.g., `2026.06.02-8c11d9f`).
6. **Workspace trust prompt** — in headless mode, use `--trust` to auto-approve; without it, `--print` may hang waiting for trust confirmation.
7. **Not suitable for interactive multi-turn** — unlike Claude Code's interactive mode, Cursor CLI's strength is one-shot headless tasks. For multi-turn, use the IDE or script sequential `--print` calls.

## Verification Checklist

- [ ] `agent --version` returns a date-stamped version
- [ ] `agent --list-models` shows available models (>0 entries)
- [ ] `agent --print --model sonnet-4 "echo hello"` works in headless mode
- [ ] cursor.com is reachable without proxy: `curl -sI https://cursor.com`
- [ ] CURSOR_API_KEY is set in .env or config
