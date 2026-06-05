# Agent Capability Tests — 2026-06-03

Actual test results from the NUC environment.

## Cursor CLI (agent)

| Property | Value |
|----------|-------|
| Version | 2026.06.02-8c11d9f |
| Binary | ~/.local/bin/agent |
| OAuth | kate_2012@outlook.com (Pro) |
| Models | auto, composer-2.5, composer-2.5-fast(default), grok-build-0.1, grok-4.3, kimi-k2.5 |

**Headless test** (agent --print --trust --model composer-2.5 "prompt"): ✅

**Built-in tools tested:**
- File read/write: ✅
- File search: ✅
- Shell execution: ✅ (needs --force or --yolo)
- MCP WebFetch: ✅ (built-in)
- JSON output: ✅ (--output-format json)
- Worktree isolation: ✅

**MCP support:** agent mcp list / list-tools / login / enable/disable — all work. External MCP servers need .cursor/mcp.json config.

**Limitations:**
- Sandbox mode not available (needs AppArmor)
- Shell commands denied by default in headless — must add --force

## Codex CLI

| Property | Value |
|----------|-------|
| Version | v0.136.0 |
| Binary | ~/.hermes/node/bin/codex |
| Model | GPT-5.5 (OpenAI) |
| Provider | OpenAI |

**Network:** Needs HTTPS_PROXY=http://127.0.0.1:7890. Direct connection to chatgpt.com is blocked.

**Cold start issue:** First call after idle takes ~30s+ due to model refresh timeout. Error: "failed to refresh available models: timeout waiting for child process to exit". Second call is fast.

**Headless test** (HTTPS_PROXY=... codex exec --skip-git-repo-check "prompt"): ✅

**Featured tools (partial list):** exec_command, apply_patch, web_search, browser_use, computer_use, image_gen, MCP, plugins/skills

**Feature flags:** 43 total, 19 stable active. Includes multi_agent, hooks, plugins.

**Pre-installed skills:** imagegen, openai-docs, plugin-creator, skill-creator, skill-installer

## Claude Code

Installed at ~/.hermes/node/bin/claude v2.1.159. Configured for MiMo API Anthropic-compatible endpoint. Needs config verification before production use.

## DeepSeek V4 Pro / MiMo V2.5 Pro

Both accessible via API only — no shell/file access. Both responded with high-quality architectural advice in consultation. See dual-model-consultation.md.
