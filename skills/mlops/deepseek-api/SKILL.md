---
name: deepseek-api
description: >
  "Use DeepSeek API — model names, context windows, pricing, KV cache, usage tracking limitations, and Hermes integration notes."
version: 1.0.0
compatibility: Hermes Agent
metadata:
  hermes:
    tags: [deepseek, API, llm, pricing, models]
    related_skills: [xiaomi-mimo-api, hermes-agent]
    trigger: manual
---

# DeepSeek API

This skill covers using DeepSeek's cloud API for model inference — model selection, context windows, pricing, KV caching, and the key limitation that DeepSeek does not expose a programmatic usage/token-query endpoint.

## Quick Reference

| Model | Model Name (API) | Context Window | Max Output | Thinking Mode |
|-------|-----------------|:--------------:|:----------:|:-------------:|
| V4 Flash | `deepseek-v4-flash` | **1M** ✅ | 384K | Supported (default) |
| V4 Pro | `deepseek-v4-pro` | **1M** ✅ | 384K | Supported |

Both use the same BASE URL: `https://api.deepseek.com`

## ⚠️ Multimodal / Vision — NOT Supported via API

**DeepSeek V4 Flash and V4 Pro do NOT support image input via the API.** The only content type accepted in the `content[]` array is `"type": "text"`. Attempting `"type": "image_url"` returns:

```json
{"error": {"message": "unknown variant `image_url`, expected `text`"}}
```

DeepSeek's "识图模式" (image recognition mode, opened May 9, 2026) is a **Web/App product feature** on chat.deepseek.com — it is **not** available through the API endpoint (`api.deepseek.com`).

### Hermes Vision Architecture

Hermes routes vision requests (`vision_analyze` tool) through a **separate `vision` config section** in `config.yaml`, entirely independent of the main model:

```yaml
vision:
  base_url: https://api.xiaomimimo.com/v1   # ← independent of model.base_url
  model: mimo-v2-omni                         # ← independent of model.default
  provider: openai
```

- `model.default: deepseek-v4-flash` → text-only chat
- `vision.model: mimo-v2-omni` → vision/image analysis (MiMo API)

This design is **correct and expected** — DeepSeek V4 API simply has no vision capability.

## Pricing (DeepSeek V4 Flash)

| Item | Price |
|------|:-----:|
| Input (cache miss) | ¥1 / 1M tokens |
| Input (cache hit) | ¥0.02 / 1M tokens (50x cheaper) |
| Output | ¥2 / 1M tokens |

⚠️ **Cost estimate trap**: Simple chat estimates (e.g. ~¥0.08–0.16/day) are wildly wrong for agent-mode usage with tool calling and multi-step reasoning. See [Agent-Mode Token Burn](#agent-mode-token-burn) below.

## Context Window — 1M is Native

**No special configuration is needed.** The model `deepseek-v4-flash` at the standard API endpoint already supports 1M context tokens. You do not need to pass any extra parameters, change the model name, or set a different base URL.

### How Hermes Handles It

Hermes gateway is aware of the 1M context window. Compression settings in `config.yaml` default to:
- `threshold: 0.5` — compress when context reaches 50% (~500K tokens)
- `target_ratio: 0.2` — compress down to ~200K tokens
- `protect_last_n: 20` — keep last 20 messages intact
- `protect_first_n: 3` — keep first 3 messages

The gateway log confirms: `threshold: 85% of 1,000,000 = 850,000` tokens for session hygiene (when `threshold` is overridden), meaning Hermes uses the model's true 1M ceiling internally.

For day-to-day chat (10-50 turns), compression rarely triggers. Only long multi-hour sessions with heavy tool use (hundreds of turns) will hit the threshold.

## KV Cache (Contextual Hard Disk Caching)

Enabled by default for all users — no code changes needed. Cache rules:
- **Request-end caching**: the end position of user input and model output are cached as "prefix units"
- **Common-prefix detection**: if multiple requests share a prefix, that prefix gets cached independently
- **Fixed-interval caching**: long inputs/outputs get cached at regular token intervals
- Cache hit/miss is reported in API response via `usage.prompt_cache_hit_tokens` and `usage.prompt_cache_miss_tokens`
- Cache takes seconds to build, auto-evicts after hours/days of non-use

**Key benefit for conversation agents**: System prompt + conversation prefix gets cached after the first request, making subsequent turns in the same session ~50x cheaper for the cached portion.

## Agent-Mode Token Burn — Critical Reality Check

**Agent-style usage consumes dramatically more tokens than simple chat.** Do not use naive chat extrapolation (/chat completions with a single user message) to estimate agent costs.

### Why agent-mode burns more

| Factor | Impact |
|--------|:------:|
| System prompt + tool schemas | Each API call sends the full system prompt (~2-5K tokens) plus tool definitions (~5-15K tokens) |
| Tool call round-trips | One user message → model thinks → calls tool → tool returns result → model processes result → responds. Each leg is a separate API call with full context |
| Subagent delegation | Each subagent (delegate_task) creates its own conversation with its own system prompt and tool set |
| Compression overhead | Long sessions accumulate conversation history. Even compressed, the ~2-3K compressed summary is re-sent on every turn |

### Real-world measurements (from actual Hermes session data)

| Scenario | API Calls / Day | Total Tokens | Daily Cost |
|----------|:---------------:|:------------:|:----------:|
| Simple Q&A chat | ~50-80 | ~50-80K | ~¥0.08-0.16 |
| **Agent mode with tool use** | **~350-400** | **~1.5-2.0M** | **~¥1.50-2.50** |

Source: 2026-06-01 session — 386 API calls in ~5 hours, balance dropped from ¥68.32→¥66.41 (¥1.91 actual cost). This was a typical agent session with tool calls, code execution, web searches, file operations, and subagent delegation.

**Never estimate agent-mode costs by extrapolating from simple chat token counts. Always check actual balance change instead.**

## Balance Tracking — The Only Reliable Cost Monitor

Since DeepSeek has no usage query API, the only way to track actual spend is to **compare balance snapshots over time.**

### Technique

```python
# Query balance
GET https://api.deepseek.com/user/balance
→ Response: {"balance_infos": [{"currency": "CNY", "total_balance": "66.41"}, ...]}

# Track with history
balance_history = [
  {"timestamp": "2026-06-01 04:09", "CNY": 68.32},
  {"timestamp": "2026-06-01 09:15", "CNY": 66.41},  # ¥1.91 spent in ~5 hours
]

# Cost = previous_balance - current_balance
```

### Workflow
1. Run `/user/balance` periodically (e.g. via cron) and save to a JSON file
2. Compare consecutive entries to get actual per-period spend
3. The `check_deepseek_balance.py` reference script implements this

See `references/pricing-context-windows.md` for the balance history format and tracking script layout.

**DeepSeek does NOT provide a programmatic API to query token usage.** The following endpoints all return 404:

```
GET /dashboard/billing/usage         ❌ 404
GET /v1/dashboard/usage              ❌ 404
GET /user/usage                      ❌ 404
GET /v1/dashboard/billing/usage      ❌ 404
```

This differs from OpenAI, which exposes `/v1/dashboard/billing/usage`.

### Workarounds

1. **Manual**: visit [platform.deepseek.com](https://platform.deepseek.com) → Usage page
2. **Hermes state.db (best local workaround)**: Hermes already tracks per-session token counts internally. You don't need to build from scratch. Query `~/.hermes/state.db`:

   ```sql
   -- All-time token totals
   SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens),
          COUNT(*) as sessions, SUM(api_call_count)
   FROM sessions;

   -- Today's usage
   SELECT SUM(input_tokens), SUM(output_tokens),
          SUM(estimated_cost_usd), SUM(actual_cost_usd)
   FROM sessions WHERE started_at > strftime('%%s', 'now', 'start of day');

   -- Per-session breakdown
   SELECT substr(id,1,24), model, input_tokens, output_tokens,
          actual_cost_usd, cost_status, api_call_count,
          datetime(started_at, 'unixepoch')
   FROM sessions ORDER BY started_at DESC LIMIT 10;
   ```

   The sessions table has these columns: `id`, `model`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`, `estimated_cost_usd`, `actual_cost_usd`, `cost_status`, `cost_source`, `pricing_version`, `message_count`, `api_call_count`, `started_at`, `ended_at`, `end_reason`.

   ⚠️ **Known limitation**: For DeepSeek V4 Flash, `cost_status` is `'unknown'` and `actual_cost_usd` is `NULL` because Hermes' built-in pricing table has no entry for `deepseek-v4-flash`. Token counts are accurate; cost needs manual calculation from pricing or balance snapshots.

3. **Estimation from session data**: Hermes gateway logs session hygiene data showing total tokens used per compression event:
   ```
   Session hygiene: 401 messages, ~266,313 tokens (actual)
   ```
   Average ~664 tokens per message (input + output). But this is the cumulative context size at compression time, not per-API-call totals — the state.db session-level `input_tokens` is the authoritative figure.

### Session DB vs Balance: Known Discrepancy

Session-level token totals from state.db do not equal the tokens billed by the API. This is because each API call sends the full conversation context (system prompt + history + new user message + tool schemas + tool results), and the session DB records the **sum across all API calls**, while the naive estimate from a single message count misses three layers of overhead:

- System prompt + tool definitions: ~7-15K tokens per API call
- Per-tool-call round-trips: each tool call and its result is a separate API call with full context
- Subagent delegation: child agents have their own full contexts

Empirically (2026-06-01 data): 448K session tokens → ¥1.91 actual cost. Using the formula (input×¥1 + output×¥2)/1M would give only ~¥0.57 for the same data, meaning the difference comes from the **per-API-call overhead** that's included in the billed count but aggregated differently in the session table. Always prefer **balance snapshots** for cost accuracy.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Chat completions (OpenAI-compatible) |
| `/v1/models` | GET | List available models |
| `/user/balance` | GET | Check remaining balance (CNY + USD) |

The balance endpoint returns:
```json
{
  "balance_infos": [
    {"currency": "CNY", "total_balance": "69.05"},
    {"currency": "USD", "total_balance": "0.00"}
  ],
  "is_available": true
}
```

For Anthropic-format API: `https://api.deepseek.com/anthropic`

## Hermes Dashboard Integration — Analytics & Cost Tracking

Hermes has a built-in web dashboard (React + FastAPI) with a full Analytics page at `/api/analytics/usage`. It queries the session database (`state.db`) and can display token usage, model breakdown, daily charts, and cost — **if** the model's pricing entry exists.

### Building and Running

```bash
cd ~/.hermes/hermes-agent/web
npm install && npm run build
hermes dashboard --port 9119 --host 127.0.0.1
```

The `hermes dashboard` CLI command was introduced in v0.15.x. Enable the TUI Chat tab with `--tui`. See `references/dashboard-analytics-setup.md` for troubleshooting common startup errors (dashboard_auth module, `--insecure` gate, `--skip-build`).

### The Analytics Data Flow

```
API Response (usage.prompt_tokens + usage.completion_tokens + ...)
  → AIAgent records CanonicalUsage into state.db sessions table
    → Columns: input_tokens, output_tokens, cache_read_tokens, reasoning_tokens,
                estimated_cost_usd, actual_cost_usd, cost_status, cost_source, api_call_count
      → Dashboard API /api/analytics/usage?days=N queries sessions table
        → Returns daily[], by_model[], totals{}, skills{}
```

### Adding Missing Pricing

Hermes calculates `actual_cost_usd` using an internal pricing table in `agent/usage_pricing.py`. If a model's cost is `$0` / `cost_status: unknown`, the pricing entry is missing. To add:

1. Find the pricing in the model provider's docs
2. Convert to USD per million tokens
3. Add a `PricingEntry` to `_OFFICIAL_DOCS_PRICING` dict, keyed by `(provider, model)`

Example (added 2026-06-01 for DeepSeek V4 Flash):

```python
(
    "deepseek",
    "deepseek-v4-flash",
): PricingEntry(
    input_cost_per_million=Decimal("0.14"),
    output_cost_per_million=Decimal("0.28"),
    cache_read_cost_per_million=Decimal("0.0028"),
    source="official_docs_snapshot",
    source_url="https://api-docs.deepseek.com/quick_start/pricing",
    pricing_version="deepseek-pricing-2026-06-01",
),
```

**Timing:** pricing is applied at session *recording* time. Existing sessions with `cost_status: unknown` are not retroactively recalculated. Only new sessions after adding the entry will have `actual_cost_usd` populated.

### Generating Offline Analytics Snapshots

If the Dashboard is inaccessible, you can generate a local HTML snapshot directly from state.db. See `scripts/analytics_snapshot.py` in this skill directory — it queries the sessions table and outputs a Chart.js HTML page with:

- Today's token totals and estimated cost
- 30-day running cost
- Daily bar chart (input vs output)
- Per-model breakdown
- Per-day detail table

## Reference Scripts (in this skill directory)

- `scripts/check_balance.py` — Query DeepSeek `/user/balance`, save to history JSON, compare with previous entry to report actual spend. Runs without sudo, no external deps.
- `scripts/analytics_snapshot.py` — Generate offline HTML snapshot of token usage analytics from state.db. No API keys needed. Outputs `hermes_analytics_snapshot.html` in the current directory.

## References (in this skill directory)

- `references/model-comparison-testing.md` — Methodology and real session data for comparing V4 Pro vs V4 Flash on the same task. Includes test script pattern, metrics to compare, and guidance on when to use each model.

## Claude Code Integration (Anthropic-Compatible API)

DeepSeek exposes an Anthropic-format API endpoint at `https://api.deepseek.com/anthropic`. This lets Claude Code use DeepSeek models.

### Configuration

```bash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=<your-deepseek-api-key>
export ANTHROPIC_MODEL=deepseek-v4-pro[1m]       # 1M context via [1m] suffix
export ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro[1m]
export ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro[1m]
export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash
export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash
export CLAUDE_CODE_EFFORT_LEVEL=max
```

### Key details
- `deepseek-v4-pro[1m]` — `[1m]` suffix enables 1M context (only for Anthropic endpoint; non-Claude API uses the same model name without suffix). Without `[1m]`, default is **64K**.
- `deepseek-v4-flash` — cheaper model for sub-agents and lightweight tasks
- Web Search works natively in Claude Code via the Anthropic endpoint
- **Auth env var**: use `ANTHROPIC_AUTH_TOKEN` (not `ANTHROPIC_API_KEY`). Claude Code v2+ sends this value as the `x-api-key` header to the custom base URL. Using `ANTHROPIC_API_KEY` may work but is deprecated.
- **Auto-mapping defaults**: DeepSeek maps `claude-opus-*` → `deepseek-v4-pro`, `claude-sonnet-*` / `claude-haiku-*` → `deepseek-v4-flash`. **Override per tier** with explicit `ANTHROPIC_DEFAULT_*_MODEL` vars. Common pattern: set `SONNET` to `deepseek-v4-pro[1m]` for reasoning-heavy agent work, keep `HAIKU` as `deepseek-v4-flash` for quick sub-agent tasks.

### Persistent (~/.bashrc)

```bash
cat >> ~/.bashrc << 'EOF'
# Claude Code → DeepSeek
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_MODEL=deepseek-v4-pro[1m]
export ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro[1m]
export ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro[1m]
export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash
export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash
export CLAUDE_CODE_EFFORT_LEVEL=max
EOF
```

> **Secrets handling**: Add `ANTHROPIC_AUTH_TOKEN` separately — either inline in `~/.bashrc` (convenient for personal dev boxes) or in a sourced secrets file. Do not hardcode tokens in shared/committed scripts. If adding inline, place it directly after the block above:
> ```bash
> export ANTHROPIC_AUTH_TOKEN=sk-...
> ```

### Switching providers

When switching between providers (e.g. MiMo → DeepSeek), delete the old export lines before adding new ones. The key changes per provider:

| Provider | `ANTHROPIC_BASE_URL` | Auth var |
|----------|---------------------|----------|
| DeepSeek | `https://api.deepseek.com/anthropic` | `ANTHROPIC_AUTH_TOKEN` |
| MiMo | `https://api.xiaomimimo.com/anthropic` | `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY` |

Old env vars that linger (especially `ANTHROPIC_BASE_URL`) silently override new config if left in the file. Check with `grep 'ANTHROPIC' ~/.bashrc` after editing.

### Verification

Run a live test after configuration:

```bash
claude --print "用中文打个招呼"
# Expected: 你好！有什么我可以帮你的吗？😊
```

If it fails, debug with:

```bash
claude --print "hi" --debug-file /tmp/cc_debug.log
grep -E 'auth|header|401|model=' /tmp/cc_debug.log
# Expected: `has Authorization header: true`, `model=deepseek-v4-pro[1m]`
# Problematic: `has Authorization header: false`, `model=claude-opus-4-8[1m]`
```

### Pitfalls

**1. API key truncated in bashrc by shell.** When writing an API key to `~/.bashrc` via `sed` or inline `echo`, special characters (especially `$` in tokens like `sk-...`) cause shell interpolation, silently truncating the value. The key goes from 35 chars to 13 chars, and DeepSeek returns 401.

   **Detection**: Compare lengths programmatically — not by eyeball:
   ```python
   # Check bashrc key length vs .env key length
   with open('/home/duruo/.bashrc') as f:
       for l in f:
           if 'ANTHROPIC_AUTH_TOKEN' in l:
               print(f'bashrc: {len(l.strip().split(\"=\",1)[1])} chars')
   ```
   If bashrc is shorter than the .env key (e.g. 13 vs 35), rewrite using Python, not shell.

   **Fix**: Use Python to write the key safely:
   ```python
   import re
   with open('/home/duruo/.bashrc') as f:
       c = f.read()
   c = c.replace('ANTHROPIC_AUTH_TOKEN=<old-truncated-key>',
                 f'ANTHROPIC_AUTH_TOKEN=<correct-key-from-env>')
   with open('/home/duruo/.bashrc', 'w') as f:
       f.write(c)
   ```

**2. `CLAUDE_CODE_SIMPLE=1` is required for API-key-only auth.** Without it, Claude Code tries OAuth + keychain, stalling on a headless NUC. Always set:
   ```bash
   export CLAUDE_CODE_SIMPLE=1
   ```

**3. Auth env var must be `ANTHROPIC_AUTH_TOKEN`, not `ANTHROPIC_API_KEY`.** Claude Code v2+ reads `ANTHROPIC_AUTH_TOKEN` and sends it as the `x-api-key` header. Using `ANTHROPIC_API_KEY` alone results in `has Authorization header: false` in the debug log. Both `x-api-key` and `Authorization: Bearer *** work with DeepSeek's Anthropic endpoint, but Claude Code only uses the former.

**4. `[1m]` suffix enables 1M only on the Anthropic endpoint.** On the OpenAI-compatible endpoint (`/v1/chat/completions`), all DeepSeek models natively support 1M — no suffix needed. On the Anthropic endpoint (`/anthropic/v1/messages`), append `[1m]` to activate 1M. Without the suffix, the model defaults to **64K**.

**5. `--print` mode times out on long prompts.** Claude Code with DeepSeek backend fails on prompts >500 chars in `--print` mode (timeout after 120-180s). DeepSeek's Anthropic endpoint has higher per-request latency than Anthropic's own API, and Claude Code's startup overhead (plugin SessionStart hooks, skill loading) compounds it. **Mitigations:** keep prompts concise (key-value bullets, not prose); split into sequential short prompts; increase Hermes `timeout` to 180s+; use `--bare` to skip plugin overhead when plugins aren't needed.

## Hermes Integration

In `~/.hermes/.env`:

```
DEEPSEEK_API_KEY=<your-key>
```

In `~/.hermes/config.yaml`:

```yaml
model:
  default: deepseek-v4-flash
  provider: deepseek
  base_url: https://api.deepseek.com
```

No fallback providers, no fan-out — DeepSeek is used as the single provider.

## Pitfalls

- **No programmatic usage querying**. If the user wants a "token usage dashboard", you must build local tracking from API response objects.
- **Cache is "best effort"** — not guaranteed 100% hit rate. Early turns in a session always miss.
- **1M context is for input only**. Max output is 384K tokens.
- **1M context doesn't mean 1M is always used**. Hermes compression defaults to compressing at 50% (~500K) to save costs. If the user wants the full 1M available, compression `threshold` can be increased.
- **Dashboard startup: missing `dashboard_auth` module**. The installed venv (`pip install hermes-agent`) may not include `hermes_cli/dashboard_auth/`. Fix: `cd <source> && pip install -e .` from the git checkout. The error is `ModuleNotFoundError: No module named 'hermes_cli.dashboard_auth'`.
- **Dashboard auth gate on `0.0.0.0`**. Binding to non-loopback requires `--insecure` if no auth provider plugin is installed. On trusted home networks, `--host 0.0.0.0 --insecure` is safe; otherwise use SSH tunnel.
