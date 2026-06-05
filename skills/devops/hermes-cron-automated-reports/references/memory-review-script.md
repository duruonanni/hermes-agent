# Memory Review no_agent Script

Replaces the LLM-driven weekly memory review cron that kept failing with Feishu 99992402.

The script reads MEMORY.md and USER.md, computes stats (line count, char count, entry count), and flags entries over 200 characters. Output is short, clean plain text — delivered as-is by the `no_agent=True` cron.

Full path: `~/.hermes/scripts/memory_review.py`

## Architecture

```
Python script (memory_review.py)
  ├── Read MEMORY.md + USER.md from ~/.hermes/memories/
  ├── Count lines, characters, entries
  ├── Detect entries >200 chars
  ├── Print summary to stdout
  └── cron scheduler delivers stdout as plain text message
```

## Cron Job

```python
cronjob(
    action='create',
    name='weekly-memory-review',
    schedule='0 3 * * 1',     # Monday 3am Beijing (= Sunday 19:00 UTC)
    no_agent=True,
    script='memory_review.py',
)
```

## Limitations vs LLM Review

| Capability | no_agent script | LLM-driven |
|---|---|---|
| Char/line/entry stats | ✅ | ✅ |
| Long entry detection | ✅ | ✅ |
| Duplicate detection | ❌ | ✅ |
| Merge suggestions | ❌ | ✅ |
| Archive suggestions | ❌ | ✅ |
| Feishu 99992402 risk | ✅ None | ❌ High |

For deep analysis (merge/archive suggestions), run a manual `hermes` chat prompt asking for memory review instead.

## Pitfalls

- **Script must not use box-drawing chars** (`━`, `─`, `│`) in any printed output. Even in no_agent mode, these still appear in the delivered message.
- **Threshold of 200 chars** is hardcoded. If memory entries shrink/change, adjust `threshold` parameter.
- **Does not read USER.md for the same stats** currently — only MEMORY.md entries are flagged as "long". Update the script if USER.md needs the same treatment.
