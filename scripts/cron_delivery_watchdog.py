#!/usr/bin/env python3
"""Check all cron jobs are healthy — runs every 5min via cron.

Excludes self (cron-delivery-watchdog) from checks to avoid
self-referential error loop. Skips stale "Script not found" errors
if the script file now exists.
"""

import json, os, sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)


def load_jobs():
    path = os.path.join(HERMES_HOME, "cron", "jobs.json")
    with open(path) as f:
        return json.load(f)["jobs"]


def script_exists(job):
    """Check if the referenced script file currently exists."""
    script = job.get("script")
    if not script:
        return True
    path = os.path.join(SCRIPTS_DIR, script)
    return os.path.isfile(path)


def main():
    jobs = load_jobs()
    issues = []

    for j in jobs:
        name = j["name"]
        jid = j["id"][:12]

        # Skip self — break the self-referential loop
        if jid == "99bc925e45cc":
            continue

        # Skip paused jobs
        if j.get("paused_at"):
            continue

        # Check last status
        if j.get("last_status") == "error":
            err = j.get("last_error", "unknown")

            # Suppress stale "Script not found" if the file now exists
            if "Script not found" in err and script_exists(j):
                continue

            issues.append(f"⚠️ [{name}] last run error: {err[:240]}")

        # Check if overdue (next_run is in the past + 5min grace)
        next_run = j.get("next_run_at")
        if next_run:
            try:
                nr = datetime.fromisoformat(next_run)
                if nr < NOW - timedelta(minutes=5) and j.get("enabled"):
                    issues.append(f"⏰ [{name}] overdue — next run was {nr.strftime('%H:%M')}")
            except Exception:
                pass

    if issues:
        for i in issues:
            print(i)
        sys.exit(1)
    # Silent on success

if __name__ == "__main__":
    main()
