# Hermes Dashboard Analytics Setup

## Startup Troubleshooting

### Error: `ModuleNotFoundError: No module named 'hermes_cli.dashboard_auth'`

The `dashboard_auth` module lives in the source tree, not the installed venv. Fix:

```bash
cd ~/.hermes/hermes-agent
pip install -e .
```

This also updates the web_dist path. After installing, verify:

```bash
python -c "from hermes_cli.dashboard_auth.routes import router; print('OK')"
```

### Error: `Refusing to bind dashboard to 0.0.0.0 — the OAuth auth gate engages`

Dashboard binds to 127.0.0.1 by default. Using `--host 0.0.0.0` triggers the OAuth auth gate, which requires a `DashboardAuthProvider` plugin (e.g. `plugins/dashboard_auth/nous`). On a home network behind a router, use `127.0.0.1` + SSH tunnel, or pass `--insecure` to bypass the gate.

```bash
# Local only (SSH tunnel needed)
hermes dashboard --port 9119 --host 127.0.0.1

# Direct LAN access (home network only)
hermes dashboard --port 9119 --host 0.0.0.0 --insecure
```

### SSH Tunnel from Another Machine

```bash
# From the client machine
ssh -L 9119:localhost:9119 user@nuc-ip
# Then open http://localhost:9119 in browser
```

## Known Limitation: cost_status = 'unknown'

For models without a pricing entry, `state.db` stores:
- `actual_cost_usd = NULL`
- `cost_status = 'unknown'`
- `cost_source = 'none'`

Token counts (`input_tokens`, `output_tokens`) are still accurate. For cost, either:
1. Add pricing to `agent/usage_pricing.py` (takes effect for new sessions)
2. Use balance snapshots from `check_deepseek_balance.py`
3. Calculate manually: cost = (input_tokens × input_rate + output_tokens × output_rate) / 1,000,000

## Session DB Analytics Queries

```sql
-- Today's totals
SELECT SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens),
       COUNT(*), SUM(api_call_count)
FROM sessions WHERE started_at > strftime('%s', 'now', 'start of day');

-- Last N days daily
SELECT date(started_at, 'unixepoch') as day,
       SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens),
       SUM(api_call_count), COUNT(*)
FROM sessions WHERE started_at > unixepoch('now', '-30 days')
GROUP BY day ORDER BY day;

-- Per-model breakdown
SELECT model, SUM(input_tokens), SUM(output_tokens),
       COUNT(*), SUM(api_call_count)
FROM sessions WHERE model IS NOT NULL
GROUP BY model ORDER BY SUM(input_tokens) + SUM(output_tokens) DESC;

-- Latest sessions with cost status
SELECT substr(id,1,24), model, input_tokens, output_tokens,
       actual_cost_usd, cost_status, api_call_count,
       datetime(started_at, 'unixepoch')
FROM sessions ORDER BY started_at DESC LIMIT 10;
```

## HTML Snapshot Generation

When dashboard is inaccessible, use `scripts/analytics_snapshot.py` which queries state.db directly and generates `hermes_analytics_snapshot.html` (Chart.js, dark theme, daily chart + tables). Share via:
- Feishu: `MEDIA:/path/to/hermes_analytics_snapshot.html`
- Telegram/Discord: drag and drop the HTML file
