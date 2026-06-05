# Custom Cron Scripts Audit

Last audit: 2026-06-05
Branch: `local/cron-scripts` (commit `be28d1197`)

## Script Inventory

| Script | Runtime | Git Tracked | Type | Description |
|--------|---------|-------------|------|-------------|
| `check_deepseek_balance.py` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Python | DeepSeek balance query API |
| `cron_delivery_watchdog.py` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Python | Cron job health monitor (runs every 5min, checks other jobs) |
| `daily_api_summary.py` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Python | Daily API status brief (DeepSeek + MiMo + GPT) |
| `memory_review.py` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Python | Weekly memory review (Mon 03:00) |
| `mihomo_watchdog.sh` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Bash | Proxy (mihomo/Clash Meta) health watchdog |
| `run_memory_sync.sh` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Bash | Memory sync runner |
| `sync_memory_to_feishu.py` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Python | Memory-to-Feishu document sync |
| `weekly_update.sh` | ✅ ~/.hermes/scripts/ | ✅ local/cron-scripts | Bash | Weekly Hermes update with proxy+TLS fix |

## Git Tracking Status

- **Branch**: `local/cron-scripts` (created 2026-06-05 from main)
- **Remote**: `origin/local/cron-scripts` pushed successfully
- **All 8 scripts**: committed in a single batch commit `be28d1197`

## Audit Commands

```bash
# Check which scripts are git tracked
cd ~/src/hermes-agent
git ls-files scripts/                          # tracked files
git ls-files --others --exclude-standard scripts/  # untracked files

# Compare runtime vs git copies
diff ~/.hermes/scripts/<name> ~/src/hermes-agent/scripts/<name>

# Copy runtime-only scripts to git tracking dir
cp ~/.hermes/scripts/<name> ~/src/hermes-agent/scripts/

# Commit workflow for cron-scripts branch
git checkout local/cron-scripts
git add scripts/<name>
git commit -m "chore(scripts): <description>"
ALL_PROXY=http://127.0.0.1:7890 git push origin local/cron-scripts
```

## Pitfalls

- **Do NOT commit to main**: custom scripts go to `local/cron-scripts` branch only
- **Sync both copies**: always update both `~/.hermes/scripts/` (runtime) and `~/src/hermes-agent/scripts/` (git)
- **Load skill first**: use `skill_view('hermes-self-maintenance')` before modifying any cron script
- **Verify after push**: `hermes cron list` to confirm script paths are valid
