# Custom Skills Audit

Last audit: 2026-06-05

## Background

Custom skills live in `~/.hermes/skills/` — a runtime directory with no git protection.
The `local/custom-skills-tools` branch tracks a subset of them (cherry-picked from earlier recovery).
The rest exist ONLY on disk and would be lost on git reset/clean.

## How to Audit

```bash
cd ~/src/hermes-agent

# Find skills in runtime that aren't in upstream git
find ~/.hermes/skills -name "SKILL.md" -maxdepth 3 2>/dev/null | while read f; do
  dir=$(dirname "$f")
  rel="${dir#/home/duruo/.hermes/skills/}"
  name=$(basename "$dir")
  cat="${rel%%/$name}"

  upstream_skill="$HOME/src/hermes-agent/skills/$cat/$name/SKILL.md"
  upstream_optional="$HOME/src/hermes-agent/optional-skills/$cat/$name/SKILL.md"
  flat="$HOME/src/hermes-agent/skills/$name/SKILL.md"
  flat_opt="$HOME/src/hermes-agent/optional-skills/$name/SKILL.md"

  if [ -f "$upstream_skill" ] || [ -f "$upstream_optional" ] || [ -f "$flat" ] || [ -f "$flat_opt" ]; then
    :  # exists in upstream — safe
  else
    # Check if it was ever committed to any branch
    committed=$(git log --all --oneline -- "skills/$cat/$name/SKILL.md" "skills/$name/SKILL.md" 2>/dev/null | head -1)
    if [ -z "$committed" ]; then
      echo "❌ NEVER COMMITTED: $cat/$name"
    fi
  fi
done
```

## Skills Never Committed to Any Git Branch (26 found)

| Category | Skill Name | Type | Risk | Reason |
|----------|-----------|------|------|--------|
| devops | hermes-self-maintenance | Custom (user-created) | High | Core devops skill, must not lose |
| devops | self-code-management | Custom (user-created) | High | Fork management spec, must not lose |
| devops | nuc-proxy-setup | Custom (user-created) | High | Proxy setup instructions |
| devops | nuc-server-maintenance | Custom (user-created) | High | Server health procedures |
| devops | multi-agent-orchestration | Custom (user-created) | High | Multi-agent workflow |
| devops | hermes-cron-automated-reports | Custom (user-created) | Medium | Cron report workflows |
| devops | hermes-dashboard | Custom (user-created) | Medium | Dashboard setup |
| devops | hermes-gateway-platforms | Custom (user-created) | Medium | Gateway platform troubleshooting |
| devops | linux-system-relocation | Custom (user-created) | Medium | NUC relocation procedures |
| devops | hermes-memory-maintenance | Custom (user-created) | Medium | Memory maintenance workflow |
| devops | webhook-subscriptions | Custom (user-created) | Medium | Webhook setup |
| software-development | persist-environment-facts | Custom (user-created) | High | Tool install persistence — widely used |
| software-development | claude-code-setup | Custom (user-created) | High | Claude Code config |
| software-development | harness-engineering | Custom (user-created) | Medium | Engineering cybernetics |
| software-development | headless-chrome-screenshot | Custom (user-created) | Medium | Screenshot workflow |
| software-development | debugging-hermes-tui-commands | Custom (user-created) | Medium | TUI debug |
| dogfood | skill-maintenance-audit | Custom (user-created) | High | Cron-based weekly skill audit |
| dogfood | skill-lint | Custom (user-created) | High | Skill validation |
| github | github-pr-feasibility | Custom (user-created) | Medium | PR feasibility check |
| autonomous-ai-agents | hermes-web-setup | Custom (user-created) | Medium | Web search/browser setup |
| autonomous-ai-agents | cursor-cli | Custom (user-created) | Medium | Cursor CLI delegation |
| research | capability-verification | Custom (user-created) | Medium | Capability verification |
| feishu | feishu-document-api | Custom (user-created) | Medium | Feishu doc API |
| mlops | deepseek-api | Custom (user-created) | Low | API reference — re-fetchable |
| mlops | xiaomi-mimo-api | Custom (user-created) | Low | API reference — re-fetchable |
| productivity | feishu-doc-suggestion | Custom (user-created) | Medium | Feishu doc suggestion |
| productivity | personal-assistant-multi-user | Custom (user-created) | Medium | Multi-user PA workflow |
| productivity | html-to-pdf | Custom (user-created) | Low | PDF generation |
| productivity | linear | Custom (user-created) | Low | Linear task management |

## Recommended Protection Order

| Phase | Branch | Skills to Track | Effort |
|-------|--------|----------------|--------|
| 1 | `local/core-devops` | hermes-self-maintenance, self-code-management, multi-agent-orchestration, nuc-server-maintenance, nuc-proxy-setup | ~5 skills |
| 2 | `local/custom-skills` | skill-maintenance-audit, skill-lint, persist-environment-facts, claude-code-setup, harness-engineering, hermes-cron-automated-reports | ~6 skills |
| 3 | same branch | rest (lower priority) | ~17 skills |

## Recovery Command (if lost from disk)

```bash
cd ~/src/hermes-agent
git checkout local/custom-skills-tools -- skills/<category>/<name>/
```
