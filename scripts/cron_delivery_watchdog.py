#!/usr/bin/env python3
"""Cron job error delivery watchdog — runs every 5min.

Checks all cron jobs for errors and reports them to the user.
NO_AGENT mode: always exits 0 so the scheduler never marks THIS job as "error".
Output is the delivery signal (non-empty = alert, empty = silent).

Features:
  - Self-referential loop prevention (skips own job_id)
  - 15-min cooldown to avoid repeated alerts for the same issue
  - Stale "Script not found" suppression (if the file now exists)
  - Paused job skipping
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

# Cooldown: skip re-reporting the same error within this window
COOLDOWN_MINUTES = 15

# This job's own ID (skip self)
SELF_JOB_ID = "99bc925e45cc"


def load_jobs():
    path = os.path.join(HERMES_HOME, "cron", "jobs.json")
    with open(path) as f:
        return json.load(f)["jobs"]


def script_exists(job):
    script = job.get("script")
    if not script:
        return True
    path = os.path.join(SCRIPTS_DIR, script)
    return os.path.isfile(path)


def job_age_minutes(job):
    """How long ago the job last ran, in minutes."""
    ts = job.get("last_run_at")
    if not ts:
        return None
    try:
        last = datetime.fromisoformat(ts)
        return (NOW - last).total_seconds() / 60
    except Exception:
        return None


def main():
    jobs = load_jobs()
    issues = []

    for j in jobs:
        name = j["name"]
        jid = j["id"][:12]

        # Skip self — break the self-referential loop
        if jid == SELF_JOB_ID:
            continue

        # Skip paused jobs
        if j.get("paused_at"):
            continue

        if j.get("last_status") != "error":
            continue

        err = j.get("last_error", "") or ""

        # Suppress stale "Script not found" if the file now exists
        if "Script not found" in err and script_exists(j):
            continue

        # Cooldown: skip recently-reported errors to avoid noise
        age = job_age_minutes(j)
        if age is not None and age < COOLDOWN_MINUTES:
            continue

        if err:
            issues.append(f"⚠️ [{name}] {err[:240]}")
        else:
            issues.append(f"⚠️ [{name}] last run failed (no error detail)")

    if issues:
        print("\n".join(issues))

    # Always exit 0 — output IS the delivery signal.
    # Non-zero exit would mark THIS job as "error" in the scheduler,
    # creating a cascade of false alerts that mask real issues.


if __name__ == "__main__":
    main()
