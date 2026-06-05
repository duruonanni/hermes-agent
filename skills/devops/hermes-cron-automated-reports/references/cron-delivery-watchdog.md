# Cron Delivery Failure Watchdog

Monitors cron jobs for delivery failures and proactively alerts the user — no need to wait for them to notice a missed report.

## Architecture

```
no_agent=True script (cron_delivery_watchdog.py)
  ├── Reads ~/.hermes/cron/jobs.json
  ├── Compares current last_delivery_error against previous state
  ├── NEW error found → print alert message → delivered to user's chat
  └── No change → silent (no output, nothing delivered)
```

Frequency: `every 5m` — lightweight JSON read + dict compare, negligible cost.

## The Watchdog Script

Full script at `~/.hermes/scripts/cron_delivery_watchdog.py`:

```python
#!/usr/bin/env python3
"""Watchdog: check all cron jobs for delivery failures and alert the user."""
import json, os, time
from pathlib import Path

HERMES_HOME = os.path.expanduser("~/.hermes")
STATE_FILE = Path(HERMES_HOME) / "scripts" / ".cron_delivery_watchdog_state.json"

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def get_cron_jobs():
    json_path = Path(HERMES_HOME) / "cron" / "jobs.json"
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text())
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        return [
            (j.get("name", "?"), j.get("last_delivery_error"),
             j.get("last_run_at"), j.get("schedule"))
            for j in jobs
        ]
    except Exception:
        return []

def main():
    state = load_state()
    jobs = get_cron_jobs()
    alerts = []
    for name, last_error, last_run, schedule in jobs:
        if not last_error:
            continue
        prev_error = state.get(name)
        if prev_error != last_error:
            alerts.append((name, last_error, last_run, schedule))
            state[name] = last_error
    if alerts:
        now = time.strftime("%Y-%m-%d %H:%M:%S (CST)")
        print(f"⚠️ Cron 投递故障通知 — {now}")
        print()
        for name, error, last_run, schedule in alerts:
            print(f"  **任务:** {name}")
            print(f"  **时间:** {last_run or '?'}")
            print(f"  **调度:** {schedule or '?'}")
            print(f"  **错误:** {error}")
            print()
        save_state(state)

if __name__ == "__main__":
    main()
```

## Cron Job

```python
cronjob(
    action='create',
    name='cron-delivery-watchdog',
    schedule='every 5m',
    no_agent=True,
    script='cron_delivery_watchdog.py',  # relative to ~/.hermes/scripts/
)
```

## Key Design Decisions

- **Stateful comparison** — tracks `last_delivery_error` per job name. Only alerts on NEW errors, not on subsequent watchdog ticks. Prevents spam.
- **Silent when clean** — `no_agent=True` with empty stdout = nothing delivered. User never sees "all clear" noise.
- **No dependencies** — pure stdlib (json, os, time, pathlib). No sqlite3, no pip packages.
- **Escaped output** — uses compact key-value format (`**键:** 值`) for Feishu compatibility (no Markdown tables).

## Pitfalls

- **`jobs.json` format may change.** The agent that created the job should verify the JSON structure with `cronjob(action='list')` first, then adapt the parser. The script assumes either a top-level list or a `{"jobs": [...]}` dict.
- **State file path matters.** Saved under `~/.hermes/scripts/.cron_delivery_watchdog_state.json` (dotfile prefix to avoid cluttering listing). Must be writable by the cron daemon process.
- **Cron scheduler runs in the gateway.** If the gateway is down, watchdog won't fire. This is acceptable — if the gateway is down, nothing is running anyway.
- **99992402 errors on Feishu** are an ongoing issue caused by Markdown tables, Unicode arrows, or excessive formatting in agent-based cron responses. The watchdog alerts, it doesn't fix them — that requires updating the cron prompt or switching to `no_agent=True` script delivery.
