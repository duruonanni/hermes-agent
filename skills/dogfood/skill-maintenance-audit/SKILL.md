---
name: skill-maintenance-audit
description: >-
  Weekly audit of ALL skills (official + custom) that integrates skill-lint,
  baseline comparison, and GitHub issue filing for NEW problems only. Use when
  user asks to "check skills", "audit skills", or on Monday 03:30 via cron.
version: "2.1.0"
compatibility: Hermes Agent (uses skill_manage, patch, read_file, search_files tools)
metadata:
  hermes:
    tags: [hermes, skills, maintenance, audit, dogfood]
    related_skills: [hermes-agent, hermes-memory-maintenance, github-issues, skill-lint]
    trigger: cron
    cron_schedule: "30 3 * * 1"
---
# Skill Maintenance Audit

## When This Skill Activates

- User asks "check my skills", "clean up skills", "audit skills", "skill maintenance"
- Scheduled cron job (every Monday 03:30 BJT, job_id: `fa296224d64d`)
- After merging/renaming/deleting skills — to catch broken cross-references
- Before sharing skills to community — to ensure quality

## Design Principle

This skill inspects ALL skills under `~/.hermes/skills/` — both official (shipped with Hermes Agent) and custom (user-created). The workflow is:

0. **Pre-step: Run skill-lint** — delegate all metadata validation to `skill-lint` (saves/loads baseline)
1. **Compare with baseline** — detect NEW issues since last week
2. **Verify cross-references** — frontmatter + body-level
3. **Check for merge candidates, stale content, cron bindings**
4. **File GitHub issues** — for NEW problems in official skills only
5. **Report** — structured Feishu-compatible output (no Markdown tables)

Findings are split into three tracks:

- **Official skills** — cross-reference issues can be auto-fixed locally AND filed as GitHub issues upstream
- **Custom skills** — reported for user decision; only auto-fix references that are provably broken
- **Spec compliance** — trigger annotations, metadata.hermes completeness, name-dir consistency

### Critical: Local vs Upstream

Every auto-fix in the cron report is **LOCAL ONLY** — it patches the copy under `~/.hermes/skills/`. When official skills are updated (via `pip install --upgrade hermes-agent` or repo pull), local patches are overwritten. Separate GitHub issues must be filed for upstream fixes.

Use explicit language:
- "→ auto-fixed locally" (not just "→ auto-fixed")
- "→ needs upstream fix" / "→ GitHub issue #N filed"
- "→ flagged for user decision" (no action taken)

## Audit Workflow

### 0. Run skill-lint (Pre-step) — delegated to `lint.py`

Delegate all metadata validation to the dedicated lint script:

```bash
python3 /home/duruo/.hermes/skills/dogfood/skill-lint/scripts/lint.py
```

This produces structured JSON output with per-skill results (errors, warnings, auto-fixes).

**IMPORTANT:** Capture output to a file with `> /tmp/skill-lint-output.json` — do NOT rely on pipe chaining in terminal(). Large command output through pipes causes `RuntimeError: [Errno 32] Broken pipe` when the cron delivery system closes its reader side.

**NOTE:** `hermes skills validate --all` does NOT exist in v0.15.x. Use `lint.py`.

### 0b. Baseline Comparison

Load the previous week's baseline from `~/.hermes/cron/skill-lint-baseline.json`.

Compare the current lint results with the baseline. If they are identical, respond with exactly `[SILENT]`.

**Only NEW issues** (skills that went from clean to having findings) should be:
1. Logged in the audit report under "**NEW Issues Since Last Week**"
2. Automatically filed as GitHub issues if they affect official skills
3. Flagged for user attention if they affect custom skills

Save the current result as the new baseline:

```bash
python3 /home/duruo/.hermes/skills/dogfood/skill-lint/scripts/lint.py > /home/duruo/.hermes/cron/skill-lint-baseline.json
```

**Pitfall:** Baseline file permissions — the cron user must be able to write to `~/.hermes/cron/`. Ensure the directory exists.

### 0c. Filing GitHub Issues for NEW Problems

Only file issues for NEW problems detected by the baseline comparison above. Group all new findings from a single audit run into one GitHub issue.

Search for duplicates first using GitHub API, then file with:

```
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/NousResearch/hermes-agent/issues \
  -d '{"title": "...", "body": "..."}'
```

Do NOT include `labels` or `assignees` fields — most PATs lack permission.

## Pitfalls

- **Do NOT hallucinate skill names.** If a reference uses a name that looks plausible but doesn't exist, treat it as broken. Do NOT create a skill to "fix" the reference.
- **Do NOT rewrite body content.** Only fix `related_skills` YAML arrays. Flag body references for user decision.
- **Pricing in skills is always stale.** Flag for review but never update pricing numbers.
- **Merging is a user decision.** Report candidates but never execute.
- **YAML-name vs directory-name mismatch.** Directory `vllm/` may have YAML name `serving-llms-vllm`. Resolve references against YAML name, not directory basename.
- **Body-level references need different handling.** Backtick-wrapped skill names in body text are descriptive prose — flag as stale but do NOT auto-fix.
- **skill-lint dependency may go missing.** If `skill-lint` was deleted in a git cleanup (see reference `recovery-after-git-cleanup.md`):
  - Check the SKILL.md survived (skills_list may still show it in its own index)
  - Reconstruct `scripts/lint.py` from session_search history
  - Regenerate the baseline after rebuilding
  - Verify the cron job's `skills` binding is still correct
- **Custom skills in `~/.hermes/skills/` are NOT tracked by upstream git.** A `git reset --hard` or cleanup against the `~/.hermes` repo will delete them. Protect custom skills by:
  1. Keeping them in a separate git-tracked directory with symlinks, OR
  2. Maintaining a backup branch, OR
  3. Ensuring they're in `~/.hermes/skills/` and the `.hermes` repo is never force-reset

## Automatic Cron Trigger

This skill runs via cron job `fa296224d64d`:

- Schedule: Monday 03:30 BJT (`30 3 * * 1`)
- Skills bound: `[skill-maintenance-audit, skill-lint]`
- Prompt: Execute lint.py → compare with baseline → save new baseline → report

If the cron job's skills binding breaks (skill not found), fix it by:
1. Rebuild the missing skill from session_history
2. Verify it runs: `python3 ...scripts/lint.py > /tmp/test-output.json`
3. Regenerate baseline: run lint.py > skill-lint-baseline.json
4. Verify next cron run with `cronjob action='run' job_id='fa296224d64d'`

## Recovery After Git Cleanup (proven 2026-06-05)

When a git reset/cleanup on `~/.hermes` deletes custom skills:

1. **Detect:** cron job reports `⚠️ Skill(s) not found and skipped: ...`. Run `skills_list()` to confirm.
2. **Reconstruct:** Use `session_search(query="skill-name")` to find full SKILL.md + scripts from historical sessions.
3. **Rebuild:** `skill_manage(action='create', name='...', category='dogfood', content=...)` for SKILL.md. If `skill_manage(action='write_file')` fails with `ModuleNotFoundError: No module named 'tools.path_security'`, write scripts via `write_file()` directly to the resolved path.
4. **Verify:** Run the lint script: `python3 .../scripts/lint.py > /tmp/test.json` (redirect, no pipes). Check exit code and JSON shape.
5. **Regenerate baseline:** `python3 .../scripts/lint.py > ~/.hermes/cron/skill-lint-baseline.json`
6. **Verify cron:** `cronjob(action='list')` — confirm `skills` binding still correct for job `fa296224d64d`.
7. **Test run:** `cronjob(action='run', job_id='fa296224d64d')` — check `last_status: ok`.

**Key sessions for reconstruction:**
- `20260602_185748_c060e6` — Original skill creation
- `20260603_150922_79da904e` — June 3 patches (lint.py over `validate --all`, pipe chain fixes)
- `cron_fa296224d64d_*` — Cron run transcripts with full SKILL.md in user message
