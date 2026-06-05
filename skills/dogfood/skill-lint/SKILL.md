---
name: skill-lint
description: >-
  Validate SKILL.md frontmatter across all skills. Checks name-dir match,
  description length (≤1024 chars), metadata.hermes presence, trigger validity,
  related_skills resolution, and body-level dead backtick refs. Creates .pre-lint
  backups before auto-fixing broken related_skills references.
version: "1.0.0"
compatibility: Hermes Agent (stdlib Python, no external deps)
metadata:
  hermes:
    tags: [hermes, skills, lint, validation, quality]
    related_skills: [skill-maintenance-audit, hermes-agent-skill-authoring]
    trigger: manual
---
# skill-lint

Validate SKILL.md frontmatter across all skills under `~/.hermes/skills/`.

## Checks Performed

1. **Name-Dir Match** — YAML `name:` field must match directory basename
2. **Description Length** — Must be ≤ 1024 characters
3. **metadata.hermes Presence** — Check for tags, related_skills, trigger
4. **Trigger Validity** — Must be one of: `manual`, `cron`, `slash`, `preload`
5. **related_skills Resolution** — Every referenced name must exist as a valid skill (auto-fix eligible; creates `.pre-lint.SKILL.md` backup before modifying)
6. **Body-Level Dead Refs** — Backtick-wrapped skill-like names in body text → WARNING only (not auto-fixed)

## Usage

```bash
# Run lint, output JSON to stdout
python3 ~/.hermes/skills/dogfood/skill-lint/scripts/lint.py

# Save to file for comparison
python3 ~/.hermes/skills/dogfood/skill-lint/scripts/lint.py > /tmp/lint-output.json

# Read result
cat /tmp/lint-output.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['summary']['total_skills']} skills, {d['summary']['errors']} errors, {d['summary']['warnings']} warnings, {d['summary']['auto_fixed']} auto-fixed\")"
```

## Exit Codes

- `0` — Clean (no issues)
- `1` — Issues found (errors or warnings)
- `2` — Auto-fixes applied

## Related

- `skill-maintenance-audit` — Weekly cron that integrates this linter with baseline comparison
- `hermes-agent-skill-authoring` — Skill authoring conventions

## ⚠️ Recovery Note (2026-06-05)

The `scripts/lint.py` implementation was lost during the 2026-06-04 `~/.hermes` git cleanup.
The SKILL.md metadata survived because Hermes skills_list reads from its own index.

To recover from a similar loss, see `skill-maintenance-audit` → section **"Recovery After Git Cleanup"**
which documents the full step-by-step process: session_search → reconstruct → rebuild → verify → regenerate baseline.
