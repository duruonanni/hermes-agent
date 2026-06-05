# Daily HTML Report Reference

Working implementation of a rich HTML daily report that combines:
- DeepSeek API balance
- System stats (CPU/memory/disk/uptime) with progress bars
- Service health checks (SearXNG, Hermes Dashboard)

Files:
- `~/.hermes/scripts/hermes_daily_report.py` — the Python script that generates HTML
- `~/.hermes/cron/output/daily_report_YYYYMMDD.html` — saved snapshot (history)

## Key Architecture Decisions

### Why agent-based (no_agent=False) instead of no_agent=True?
MEDIA: file attachments are only processed in LLM agent responses, not in no_agent script stdout. To send an HTML file as a downloadable attachment, the cron job must be agent-based:
- Agent runs the script, saves HTML to file
- Agent delivers `MEDIA:/path/to/file.html` in its response
- Cost: ~500 tokens per run to forward the file

### Cron Schedule
Beijing time 09:00 = UTC 01:00:
```python
schedule='0 1 * * *'
```

## Script Pattern

### Collect Data
The script reads:
- DeepSeek API (`/user/balance`) for balance info
- `/proc/stat` for CPU usage
- `/proc/meminfo` for memory stats
- `df -h /` for disk usage
- `curl` health checks for SearXNG (:8888) and Dashboard (:9119)

### Generate HTML
Self-contained single-file HTML with embedded CSS (GitHub Dark theme style):
- Dark background `#0d1117`, cards `#161b22`
- Color-coded values: green `<50%`, yellow `50-80%`, red `>80%`
- Progress bars with dynamic width
- Grid layout for service health cards
- No external dependencies (no CDN fonts or scripts)

### Save History
Balance data is persisted to `~/.hermes/scripts/deepseek_balance_history.json` for trend tracking.

## Pitfalls

- **MEDIA: only works in agent responses**, not in send_message() tool calls or no_agent script stdout. Attempting `send_message(message="MEDIA:/path/file")` returns Feishu error `99992402 field validation failed`.
- **Cron job mode cannot be changed via update.** To convert from no_agent=True to no_agent=False: delete the job and recreate it. The `cronjob(action='update')` API ignores `no_agent` changes.
- **Shell date syntax in cron prompts.** `$(date +%Y%m%d)` in the cron prompt is interpreted at run time by the agent's shell, not at schedule time — this is correct behavior but the agent must use `terminal(command=...)` not shell substitution in the prompt template.
- **Script with API calls may timeout.** The first run of a script that calls external APIs (DeepSeek balance) can take 10-15s if the API is slow. Use `timeout=30` in the cron agent's terminal calls.
