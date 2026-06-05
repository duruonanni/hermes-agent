#!/usr/bin/env bash
PYTHON="/home/duruo/.hermes/venv/bin/python3"
SCRIPT="/home/duruo/.hermes/scripts/sync_memory_to_feishu.py"
DOC_ID="IfPldCubnoBqftxbrV6cRPfFn7f"
exec "$PYTHON" "$SCRIPT" --doc-id "$DOC_ID" 2>&1
