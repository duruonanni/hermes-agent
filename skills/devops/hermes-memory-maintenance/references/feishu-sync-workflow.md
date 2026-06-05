# Feishu Memory Sync Workflow

## Script Location

`~/.hermes/scripts/sync_memory_to_feishu.py`

## What It Does

Reads `~/.hermes/memories/MEMORY.md` and `~/.hermes/memories/USER.md`, then renders their content into a Feishu document. The document structure:

```
🧠 Hermes Agent 记忆备份
├── MEMORY.md — 环境事实与工具技巧
│   ├── 容量统计（quoted）
│   ├── 全文（code block）
├── USER.md — 用户画像与偏好
│   ├── 容量统计（quoted）
│   ├── 全文（code block, § 分隔的各条目）
├── 评估结论（hardcoded in build_children, from 2026-06-03）
└── 同步时间戳（footer）
```

## Usage

```bash
# Create a new document (returns URL)
python3 ~/.hermes/scripts/sync_memory_to_feishu.py

# Update existing document (in-place, deletes old blocks first)
python3 ~/.hermes/scripts/sync_memory_to_feishu.py --doc-id <DOC_ID>
```

## Existing Doc ID (this NUC)

`IfPldCubnoBqftxbrV6cRPfFn7f`

## How It Works

1. Reads `FEISHU_APP_ID` + `FEISHU_APP_SECRET` from `~/.hermes/.env`
2. Gets tenant access token from `open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
3. Builds Feishu document blocks (heading2, heading3, quote, code, text, bullet)
4. If `--doc-id` provided:
   - GET existing block count (`docx/v1/documents/{id}/blocks/{id}/children`)
   - DELETE all existing blocks via `batch_delete`
   - POST new blocks
5. If no `--doc-id`: POST to create new document
6. Outputs share URL

## Cron Automation

A shell wrapper exists at `~/.hermes/scripts/run_memory_sync.sh`:

```bash
#!/usr/bin/env bash
PYTHON="/home/duruo/.hermes/hermes-agent/venv/bin/python3"
SCRIPT="/home/duruo/.hermes/scripts/sync_memory_to_feishu.py"
DOC_ID="IfPldCubnoBqftxbrV6cRPfFn7f"

exec "$PYTHON" "$SCRIPT" --doc-id "$DOC_ID"
```

The cron job runs daily at 08:00 (local time) via `hermes cron`:

```python
cronjob(
  action='create',
  schedule='0 8 * * *',
  script='/home/duruo/.hermes/scripts/run_memory_sync.sh',
  no_agent=True,   # script output is delivered verbatim
)
```

## Block Format Notes

- **Code blocks** (type 14) are used for both MEMORY.md and USER.md full text — they preserve formatting but lose interactive syntax highlighting
- **Quote blocks** (type 15) for capacity statistics and sync timestamp
- The § separator character renders correctly in Feishu code blocks
- The script uses `children` array **order** to determine document layout — reorder the `build_children()` list to restructure
