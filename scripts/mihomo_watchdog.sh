#!/usr/bin/env bash
# Mihomo proxy health check — runs every 5min via cron
# Checks: process alive + proxy port responding

MIGOMO_PORT=${MIGOMO_PORT:-7890}
PROCESS_NAME="mihomo"

# Check if process is running
if ! pgrep -x "$PROCESS_NAME" > /dev/null 2>&1; then
    echo "❌ mihomo process NOT running"
    exit 1
fi

# Check if proxy port is responding
if ! curl -s --max-time 5 -x "http://127.0.0.1:$MIGOMO_PORT" "https://www.google.com" -o /dev/null 2>&1; then
    echo "⚠️ mihomo process alive but proxy on port $MIGOMO_PORT not responding"
    exit 1
fi

# Silent on success (cron delivery only triggers on output)
