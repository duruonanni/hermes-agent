# DuckDuckGo (ddgs) Web Search Plugin Setup

Zero-config, free, no-API-key web search backend for Hermes cron jobs.

## Why ddgs Over Alternatives

| Provider | Cost | API Key | Setup Steps |
|----------|------|---------|-------------|
| **ddgs** (DuckDuckGo) | Free | None | `pip install ddgs` → config → restart |
| SearXNG | Free (self-hosted) | None | Docker compose, port config, container runtime |
| Brave Free | Free (2000/mo) | Required | API signup, env var |
| Tavily | Paid tier | Required | API signup, env var |

For agent-based cron briefings that just need web search, ddgs is the fastest path.

## Installation

```bash
# Install the ddgs Python package in the Hermes venv
pip install ddgs

# Configure Hermes to use it
hermes config set web.backend ddgs
hermes config set web.search_backend ddgs
hermes config set web.extract_backend parallel  # or firecrawl/tavily if you have keys
```

## Restart Gateway

Web search plugins are loaded at **gateway startup**. Config changes alone are not
enough — the running gateway process caches its plugin state:

```bash
systemctl --user restart hermes-gateway
```

## How Plugin Loading Works

```
Gateway start → Load config.yaml → Discover plugin backends
                (ddgs provider loaded here)
                       │
                       ▼
New agent session ─── picks up web_search(backend=ddgs)
                       │
                       ▼
Cron scheduler session ─── also picks up backend=ddgs
```

**Important:** The `web_search` tool in an **existing agent session** (the one you're currently chatting in) will NOT see the new backend until the session is recreated — only new sessions and cron sessions pick up plugin changes. Run `cronjob(action='run', job_id='...')` to test from a fresh session.

## Verification

```bash
# Check the ddgs package is installed
pip show ddgs

# Verify config
grep -A3 "^web:" ~/.hermes/config.yaml

# Confirm gateway is running with new config
systemctl --user status hermes-gateway

# Test via a fresh cron session (not current chat session)
cronjob(action='run', job_id='<your-briefing-job-id>')
# Then check output:
cat ~/.hermes/cron/output/<job_id>/<latest>.md
```

## [SILENT] Mechanism

Agent-driven cron jobs (no_agent=False) have a built-in silent mode: if the agent
responds with exactly `[SILENT]` (nothing else), the cron scheduler suppresses
delivery entirely — no message is sent to the user.

The cron prompt template includes this instruction automatically:

```
SILENT: If there is genuinely nothing new to report, respond with exactly
"[SILENT]" (nothing else) to suppress delivery. Never combine [SILENT]
with content — either report your findings normally, or say [SILENT] and
nothing more.
```

Use cases:
- The web search provider was unavailable → suppress the error message
- The user has a holiday schedule and briefings are paused
- All categories returned "no results" → better to stay silent than deliver empty sections

**Detection:** To check if a cron job ran but suppressed output, look at the
output file:

```bash
cat ~/.hermes/cron/output/<job_id>/2026-06-04_16-37-22.md
# If the Response section says [SILENT], the agent chose to suppress delivery
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `web_search` says "No provider configured" | Gateway not restarted | `systemctl --user restart hermes-gateway` |
| Cron job output is `[SILENT]` | Agent decided not to report | Check output file for context; run `cronjob(action='run',...)` manually |
| Cron job runs but user sees nothing | Delivering to wrong origin | Check `deliver` field in `cronjob(action='list')` |
| ddgs not found | Package not installed in venv | `pip install ddgs` in the hermes venv |
