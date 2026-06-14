#!/usr/bin/env python3
"""Cron job error & delivery failure watchdog — runs every 5min.

NO_AGENT mode: always exits 0 so the scheduler never marks THIS job as "error".
Output is the delivery signal (non-empty = alert, empty = silent).

Checks both:
  - Jobs whose last run failed (last_status == "error")
  - Jobs that succeeded but couldn't deliver (last_delivery_error)
  
Self-referential loop prevention (skips own job_id).
15-min cooldown avoids repeated alerts for the same issue.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

COOLDOWN_MINUTES = 15
SELF_JOB_ID = "99bc925e45cc"


def load_jobs():
    path = os.path.join(HERMES_HOME, "cron", "jobs.json")
    with open(path) as f:
        return json.load(f)["jobs"]


def script_exists(job):
    script = job.get("script")
    if not script:
        return True
    return os.path.isfile(os.path.join(SCRIPTS_DIR, script))


def age_minutes(ts_str):
    if not ts_str:
        return None
    try:
        last = datetime.fromisoformat(ts_str)
        return (NOW - last).total_seconds() / 60
    except Exception:
        return None


def extract_exit_code(error_text):
    """Pull 'Script exited with code N' from a blob that may contain stdout."""
    for line in error_text.split("\n"):
        line = line.strip()
        if line.startswith("Script exited with code"):
            return line
    return error_text[:200]


def main():
    jobs = load_jobs()
    issues = []

    for j in jobs:
        jid = j.get("id", "")[:12]
        name = j["name"]

        # Skip self — break the self-referential loop
        if jid == SELF_JOB_ID:
            continue

        # Skip paused jobs
        if j.get("paused_at"):
            continue

        status = j.get("last_status")
        delivery_err = j.get("last_delivery_error") or ""
        status_err = j.get("last_error") or ""

        has_status_error = status == "error" and bool(status_err)
        has_delivery_error = bool(delivery_err)

        if not has_status_error and not has_delivery_error:
            continue

        # Suppress stale "Script not found" if the file now exists
        combined_errs = status_err + delivery_err
        if "Script not found" in combined_errs and script_exists(j):
            continue

        # Cooldown: skip recently-reported errors to avoid noise
        age = age_minutes(j.get("last_run_at"))
        if age is not None and age < COOLDOWN_MINUTES:
            continue

        # Build alert message
        parts = []

        if has_status_error:
            # Extract just the exit code line, not the stdout dump
            parts.append(extract_exit_code(status_err))

        if has_delivery_error:
            # Trim to first 100 chars — the rest is usually traceback noise
            d = delivery_err.strip()[:100]
            parts.append(f"📨 {d}")

        msg = " | ".join(parts)
        issues.append(f"⚠️ [{name}] {msg}")

    if issues:
        print("\n".join(issues))

    # Always exit 0 — output IS the delivery signal.
    # Non-zero exit would mark THIS job as "error" in the scheduler,
    # creating a cascade of false alerts that mask real issues.


if __name__ == "__main__":
    main()
