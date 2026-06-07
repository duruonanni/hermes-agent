#!/bin/bash
# Weekly Hermes update — with retry for transient proxy/TLS failures
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
# Proxy for GitHub access (China network)
export ALL_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# NOTE: GIT_SSL_BACKEND=openssl is NOT set here because this system's git
# is compiled against GnuTLS only ('git-http-backend: Unsupported SSL backend').
# The GnuTLS recv error (-110) is a transient proxy-level issue. Retry below.

# GnuTLS recv error (-110) is known to happen intermittently through proxies.
# Retry up to 3 times with 10s delay between attempts.
MAX_RETRIES=3
RETRY_DELAY=10

for attempt in $(seq 1 $MAX_RETRIES); do
  if [ $attempt -gt 1 ]; then
    echo "→ Retry $attempt/$MAX_RETRIES (waiting ${RETRY_DELAY}s)..."
    sleep $RETRY_DELAY
  fi

  # Use && chain instead of if/fi so $? captures the real exit code.
  hermes update && { echo "✓ Update successful on attempt $attempt"; exit 0; }
  exit_code=$?
  echo "⚠ Attempt $attempt failed with exit code $exit_code"
done

echo "✗ All $MAX_RETRIES attempts failed."
exit 1
