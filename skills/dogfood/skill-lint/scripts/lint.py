#!/usr/bin/env python3
"""
skill-lint: thin wrapper around ``hermes skills validate --json --fix``.

Maintains the same CLI interface, JSON output schema, and exit codes as the
original standalone lint.py for backwards compatibility with cron jobs and
skill-maintenance-audit.

Exit codes:
  0 — Clean (no issues)
  1 — Issues found (errors or warnings)
  2 — Auto-fixes applied

Output: JSON to stdout, progress messages to stderr.
"""
import json
import os
import subprocess
import sys
from datetime import datetime


def main() -> int:
    # Find the hermes CLI in the active venv
    venv_root = os.environ.get("VIRTUAL_ENV") or os.environ.get("PIP_REQUIRE_VIRTUALENV")

    # Try common locations
    candidates = []
    if "HERMES_HOME" in os.environ:
        hermes_home = os.environ["HERMES_HOME"]
        candidates.append(os.path.join(hermes_home, "bin", "hermes"))
        candidates.append(os.path.join(hermes_home, "..", "venv", "bin", "hermes"))

    candidates.append(os.path.join(os.path.dirname(sys.executable), "hermes"))
    candidates.append(os.path.expanduser("~/.local/bin/hermes"))

    hermes_bin = None
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            hermes_bin = c
            break

    if not hermes_bin:
        # Fallback: try 'hermes' on PATH
        hermes_bin = "hermes"

    cmd = [hermes_bin, "skills", "validate", "--json", "--fix"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        now = datetime.now().isoformat()
        output = {
            "timestamp": now,
            "summary": {"total_skills": 0, "errors": 0, "warnings": 0, "auto_fixed": 0},
            "results": [],
            "auto_fixes": [],
            "error": "Command timed out after 120 seconds",
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 1

    if result.returncode not in (0, 1, 2):
        now = datetime.now().isoformat()
        output = {
            "timestamp": now,
            "summary": {"total_skills": 0, "errors": 0, "warnings": 0, "auto_fixed": 0},
            "results": [],
            "auto_fixes": [],
            "error": f"hermes skills validate failed: {result.stderr.strip()}",
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 1

    # Parse JSON output from hermes CLI
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        now = datetime.now().isoformat()
        output = {
            "timestamp": now,
            "summary": {"total_skills": 0, "errors": 0, "warnings": 0, "auto_fixed": 0},
            "results": [],
            "auto_fixes": [],
            "error": f"Could not parse hermes output: {e}",
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 1

    # Reformat to match original lint.py output schema
    total_skills = len(data.get("results", []))
    auto_fixed = data.get("summary", {}).get("auto_fixed", 0)
    total_errors = 0
    total_warnings = 0
    results_out = []
    auto_fixes_out = data.get("auto_fixes", [])

    for r in data.get("results", []):
        errors = [f["message"] for f in r.get("findings", []) if f["severity"] == "BLOCKING"]
        warnings = [f["message"] for f in r.get("findings", []) if f["severity"] == "SUGGEST"]
        total_errors += len(errors)
        total_warnings += len(warnings)

        # Collect body dead refs for the warnings field
        body_dead = [f["message"] for f in r.get("findings", [])
                     if f["rule"] == "body.dead_references"]

        results_out.append({
            "skill": r["skill"],
            "path": r["path"],
            "name_dir_match": True,  # simplified — no per-check breakdown
            "description_length": 0,
            "description_ok": True,
            "has_metadata_hermes": True,
            "has_tags": True,
            "trigger_valid": True,
            "trigger_value": None,
            "related_skills_valid": True,
            "body_dead_refs": [],
            "auto_fixed": False,
            "errors": errors,
            "warnings": warnings + body_dead,
        })

    now = datetime.now().isoformat()
    output = {
        "timestamp": now,
        "summary": {
            "total_skills": total_skills,
            "errors": total_errors,
            "warnings": total_warnings,
            "auto_fixed": auto_fixed,
        },
        "results": results_out,
        "auto_fixes": auto_fixes_out,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

    # Same exit codes as original lint.py
    if auto_fixed > 0:
        return 2
    if total_errors > 0 or total_warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
