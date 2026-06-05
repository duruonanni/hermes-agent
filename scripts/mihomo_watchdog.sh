#!/usr/bin/env bash
# Mihomo proxy health check — runs every 5min via cron
# Checks: process alive → port listening → multi-target HTTP probe
# Silent on success (exit 0, no output).
# On failure: exit 1 with a clear message.

set -e

MIGOMO_PORT=${MIGOMO_PORT:-7890}
PROCESS_NAME="mihomo"

# 1. Process check
if ! pgrep -x "$PROCESS_NAME" > /dev/null 2>&1; then
    echo "❌ mihomo process NOT running"
    exit 1
fi

# 2. TCP port check (no external network dependency)
if ! timeout 2 bash -c "echo >/dev/tcp/127.0.0.1/$MIGOMO_PORT" 2>/dev/null; then
    echo "❌ mihomo process alive but port $MIGOMO_PORT not open"
    exit 1
fi

# 3. HTTP connectivity — try multiple targets, succeed if ANY works
#    Avoids false positives from transient target unavailability (Google rate-limiting, DNS blips, etc.)
CURL_OPTS="-s --max-time 5 -x http://127.0.0.1:$MIGOMO_PORT -o /dev/null -w %{http_code}"
TARGETS=(
    "https://www.baidu.com"
    "https://www.google.com"
    "https://github.com"
)

for target in "${TARGETS[@]}"; do
    http_code=$(curl $CURL_OPTS "$target" 2>/dev/null || echo "000")
    if [ "$http_code" != "000" ]; then
        # Any HTTP response (including 3xx/4xx/5xx) means the proxy routes traffic
        exit 0
    fi
done

# All targets failed
echo "⚠️ mihomo proxy on port $MIGOMO_PORT running but all HTTP targets unreachable"
exit 1
