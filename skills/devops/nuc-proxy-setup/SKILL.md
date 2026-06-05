---
name: nuc-proxy-setup
description: >
  Set up mihomo (Clash Meta) proxy on a NUC in China to provide
  outbound internet access for Hermes, git, npm, and other tools.
  Covers npm-based installation, subscription config, systemd service,
  runtime REST API node switching, exit IP verification, gateway proxy
  isolation, and mihomo watchdog auto-recovery cron. Use when
  the NUC needs proxy for external API access (GPT, GitHub, etc.)
  or when Docker-based proxy images are unavailable.
compatibility: Linux NUC with npm installed, no sudo required for runtime
metadata:
  author: duruo
  version: "1.5.0"
  license: MIT
  hermes:
    tags: [nuc, proxy, clash, mihomo, network, china]
    related_skills: [linux-system-relocation, nuc-server-maintenance, hermes-gateway-platforms]
globals: false
---
# NUC Proxy Setup (mihomo / Clash Meta)

## When This Skill Activates

- NUC needs outbound internet access for Hermes operations (GPT API, GitHub, Docker images)
- Current proxy is broken, missing, or outdated
- Docker Hub is unreachable (common in China) — need npm-based installation
- User asks "how do I set up Clash on the NUC"
- New subscription links need to be configured

## Architecture

```
mihomo kernel (Clash Meta)
  ↓ mixed-port 7890 (HTTP/SOCKS5)
  ├── codex / curl / git / npm ──→ External services (OpenAI, GitHub, npm)
  ├── SearXNG Docker (172.17.0.1:7890) ──→ Google, Wikipedia, Bing
  └── ❌ Hermes Gateway — DIRECT only (systemd-enforced NO_PROXY=*)
```

**Critical rule:** Hermes Gateway connects to Feishu directly (Chinese CDN), NOT through mihomo. Enforced via systemd: `HTTP_PROXY=''` `HTTPS_PROXY=''` `NO_PROXY=*`. Without this, a mihomo crash takes down the Feishu gateway (see Pitfalls: Proxy-down cascade).

The proxy uses Clash Meta (mihomo) in Rule mode: Chinese traffic goes direct, foreign traffic goes through proxy nodes. Subscription providers handle node updates automatically.

## Installation

### Step 1: Install mihomo-cli via npm

Docker Hub is typically blocked in China, so npm is the reliable install channel:

```bash
npm install -g mihomo-cli
```

This installs the `mihomo-cli` npm package which includes a kernel management layer. Commands: `mihomo`, `mihomo-cli`, `mhm`, `mh`.

### Step 2: Download the mihomo kernel

Direct download from GitHub is blocked in China. Use the `--mirror` flag:

```bash
mihomo kernel --mirror
```

This downloads via `v6.gh-proxy.org` — the kernel binary goes to `~/.mihomo-cli/kernel/mihomo`.

Verify: `~/.mihomo-cli/kernel/mihomo -v`

### Step 3: Add Subscriptions

```bash
mihomo subscription add "<SUBSCRIBE_URL>" "Name"
mihomo sub use "Name"  # activate
```

### Step 4: Generate the Working Config

Subscription configs are typically in old Clash format (`port: 7890`). mihomo v1.19+ needs `mixed-port: 7890`. Fix it:

```bash
cp ~/.mihomo-cli/subscriptions/<SubName>.yaml ~/mihomo/config.yaml
# Fix format: port → mixed-port, remove socks-port
```

Edit the first two lines:
- Change `port: 7890` → `mixed-port: 7890`
- Remove `socks-port: 7891` (merged into mixed-port)

### Step 5: Test the Proxy

```bash
~/.mihomo-cli/kernel/mihomo -d ~/.mihomo-cli/data -f ~/mihomo/config.yaml
```

In another terminal:

```bash
curl -x http://127.0.0.1:7890 https://www.google.com
curl -x http://127.0.0.1:7890 https://api.github.com
```

Expected: google → 200/302, github api → 200.

### Step 6: Systemd Service (Auto-Start on Boot)

```bash
mkdir -p ~/.config/systemd/user/
```

Write `~/.config/systemd/user/mihomo.service`:

```ini
[Unit]
Description=Mihomo Proxy (Clash Meta)
After=network-online.target

[Service]
Type=simple
ExecStart=%h/.mihomo-cli/kernel/mihomo -d %h/.mihomo-cli/data -f %h/mihomo/config.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable mihomo.service
systemctl --user start mihomo.service
systemctl --user status mihomo.service
```

### Step 7: Set Proxy Environment Variables (Selectively)

**⚠️ Do NOT put `HTTP_PROXY`/`HTTPS_PROXY` in `~/.hermes/.env`.** The gateway reads `.env` at startup, and if proxy env vars are present, the lark-oapi Feishu SDK routes ALL API calls through them. When mihomo stops, the gateway loses Feishu connectivity entirely (see Pitfalls: Proxy-down cascade).

Instead, set proxy vars only where needed:

For **terminal sessions** (codex, git, npm):
```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,.local
```

For **SearXNG Docker** (in `searxng-data/settings.yml`):
```yaml
proxies:
    all://:
      - http://172.17.0.1:7890
```

For **one-off commands**:
```bash
curl -x http://127.0.0.1:7890 https://api.github.com
```

## Subscription Management

### Switch Between Subscriptions

```bash
mihomo sub use Port384
mihomo sub use Port556
```

After switching, regenerate `~/mihomo/config.yaml` (Step 4) and restart:

```bash
systemctl --user restart mihomo.service
```

### View Status

```bash
mihomo status              # Overall status
mihomo sub list            # All subscriptions with traffic/expiry
ss -tlnp | grep mihomo     # Port check
```

### Test Node Connectivity

```bash
mihomo sub test "Name"     # Test all nodes in a subscription
mihomo sub clean "Name"    # Remove failed nodes
```

## Runtime Proxy Group Management

mihomo's REST API (`external-controller`) lets you switch proxy group selections at runtime without restarting the kernel. This is useful for testing different nodes or routing specific traffic categories.

### Prerequisite

The `external-controller` in config.yaml must use `0.0.0.0:9090` (not bare `9090`). Verify:
```bash
curl -s http://127.0.0.1:9090/version
# Should return version JSON, not "connection refused"
```

### Switch a Proxy Group's Active Node

1. **Find the group name** from config.yaml (e.g., `🤖 AI 服务`, `🐟 漏网之鱼`)
2. **URL-encode the group name** and send a PUT request:

```bash
# URL-encode the group name
GROUP=$(python3 -c "import urllib.parse; print(urllib.parse.quote('🤖 AI 服务'))")
NODE="🇺🇸 Lv.2 - US01 - 美国"

# Switch
curl -s -X PUT "http://127.0.0.1:9090/proxies/$GROUP" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"$NODE\"}"
```

3. **Verify the selection**:
```bash
curl -s "http://127.0.0.1:9090/proxies/$GROUP" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('now','?'))"
```

### List All Proxy Groups

```bash
curl -s http://127.0.0.1:9090/proxies | python3 -c \
  "import sys,json; d=json.load(sys.stdin); [print(k) for k in d if d[k]['type']=='Selector']"
```

This returns all Selector-type groups (AI, Download, Apple, Games, etc.) for inspection.

## Node Exit IP Verification

Some subscription providers label nodes by routing path, not actual exit geolocation. Always verify before relying on a node for region-locked services.

### Quick Test (Single Node)

```bash
# Set the proxy group to the target node first (see Runtime Management above)
# Then check the exit IP:
curl -s --connect-timeout 10 -x http://127.0.0.1:7890 https://httpbin.org/ip
# Returns: {"origin": "xxx.xxx.xxx.xxx"}

# Look up the IP geolocation:
curl -s "http://ip-api.com/json/xxx.xxx.xxx.xxx"
# Returns: {"country":"Hong Kong","city":"Hong Kong",...}
```

### Batch Test All Nodes in a Group

```bash
for node in "🇺🇸 Lv.2 - US01 - 美国" "🇺🇸 Lv.2 - US02 - 美国" "🇺🇸 Lv.2 - US03 - 美国"; do
  GROUP=$(python3 -c "import urllib.parse; print(urllib.parse.quote('🤖 AI 服务'))")
  curl -s -X PUT "http://127.0.0.1:9090/proxies/$GROUP" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"$node\"}" >/dev/null 2>&1
  sleep 1
  ip=$(curl -s --connect-timeout 8 -x http://127.0.0.1:7890 https://httpbin.org/ip 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('origin','?'))")
  loc=$(curl -s --connect-timeout 5 "http://ip-api.com/json/$ip" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('country','?')} - {d.get('city','?')} ({d.get('isp','?')})\")\"")
  echo "$node → $ip → $loc"
done
```

## Mihomo Watchdog (Auto-Recovery)

If mihomo stops unexpectedly (crash, config reload, manual stop), proxy-dependent services (SearXNG, codex, git) break silently. Add a no_agent cron job that checks every 5 minutes and auto-restarts:

### Script: `~/.hermes/scripts/mihomo_watchdog.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
if ss -tlnp 2>/dev/null | grep -q ':7890.*mihomo'; then
    exit 0  # alive — stay silent (no_agent cron skips delivery on empty output)
fi
if pgrep -x mihomo >/dev/null 2>&1; then
    echo "[$(date)] ⚠️  mihomo process exists but port 7890 is dead — killing stale process"
    pkill -9 mihomo 2>/dev/null || true; sleep 1
fi
echo "[$(date)] ⚠️  mihomo was down — restarting..."
systemctl --user start mihomo 2>/dev/null || echo "restart failed"
```

**Key detail:** Detection uses `ss -tlnp` not `curl`. Mihomo's mixed-port (7890) returns HTTP 400 for direct requests (it expects proxy protocol headers), so `curl -sf` incorrectly reports failure even when the proxy is working.

### Cron Registration

```bash
cronjob action=create name=mihomo-watchdog schedule='every 5m' no_agent=True script=mihomo_watchdog.sh deliver=local
```

- `no_agent=True`: script output delivered verbatim, no LLM cost
- `deliver=local`: output stays in Hermes logs (no Feishu spam)
- Design: silent when healthy (exit 0 → empty stdout → no delivery), only reports when it had to restart

### Verification

```bash
# Force-test: stop mihomo, check watchdog restarts it
systemctl --user stop mihomo
bash ~/.hermes/scripts/mihomo_watchdog.sh  # Should restart and print success
echo "Exit: $?"
ss -tlnp | grep 7890  # Should show mihomo listening
```

## Known Results (9ss.dev airport)

As of 2026-06-02, the 9ss.dev (Port384/Port556) subscription's "US" nodes all exit in Hong Kong:

| Label | Exit IP | Location |
|-------|---------|----------|
| US01-US03, US05 | 151.242.183.54 | Hong Kong — PAN-LIAN TECHNOLOGY |
| US04, US06 | Timed out | N/A |

If real US exits are needed, a different provider or subscription is required.

## Switching Configs / Adding a New Subscription

1. Add sub: `mihomo subscription add <url> <name>`
2. Activate: `mihomo sub use <name>`
3. Regenerate config: copy the new sub's yaml, fix port format
4. Restart: `systemctl --user restart mihomo.service`

## Codex CLI via Proxy

Codex CLI (OpenAI's coding agent) needs OAuth device-auth to use a GPT Plus subscription. The OAuth flow opens a browser on the user's phone/desktop — Codex just prints a URL + code.

### Proxy Setup

```bash
# Run codex login with proxy scoped to this command only
HTTPS_PROXY=http://127.0.0.1:7890 codex login --device-auth
```

**Never** set `HTTP_PROXY` in the gateway service or globally — only scope it to the codex command.

### Cloudflare Challenge, Not Geo-Block

`auth.openai.com` is behind Cloudflare. When probed with curl, it returns a JavaScript challenge page (HTTP 403, `Just a moment...`, `_cf_chl_opt` in HTML). This is **not** an IP geo-block — browsers execute the JS and pass through. Codex's `--device-auth` flow opens a real browser, so **any proxy node works**, even ones with HK/JP/SG exit IPs.

Previous false assumption that HK IPs were blocked was wrong — the 403 was the Cloudflare challenge.

### Verify Connectivity (Optional)

```bash
# Test with browser-like UA — shows Cloudflare challenge, which is fine
curl -s -x http://127.0.0.1:7890 \
  -H "User-Agent: Mozilla/5.0 (Macintosh; ...) Chrome/125.0.0.0 Safari/537.36" \
  "https://auth.openai.com" | head -5
# → "<!DOCTYPE html><html lang=\"en-US\"><head><title>Just a moment...</title>..."
```

### After Successful Auth

Codex saves credentials to `~/.codex/`. Verify the login status:

```bash
HTTPS_PROXY=http://127.0.0.1:7890 codex login status
# → "Logged in using ChatGPT"  (exit 0)
# → "Not logged in"             (exit 1 — credentials expired or auth failed)
```

Subsequent runs (`codex "do X"`) use the stored token:

```bash
HTTPS_PROXY=http://127.0.0.1:7890 codex "review the code in ~/project"
```

### Avoiding the device-auth timeout trap

`codex login --device-auth` waits for the user to visit a URL and enter a code. If run in foreground with a timeout, the command exits before the user completes the flow. **Use background mode:**

```bash
# Start in background (PTY mode for interactive output)
terminal(background=True, pty=True, command="HTTPS_PROXY=http://127.0.0.1:7890 codex login --device-auth")

# Read the device code from the process output, then wait for user to complete
cat /proc/<PID>/fd/1  # or check the PTY output

# When user confirms, verify:
HTTPS_PROXY=http://127.0.0.1:7890 codex login status
```

## Proxy-Enabled Workflows

Once the proxy is running, the following become possible from the NUC:

- **git fetch/clone/push** from/to GitHub (was timing out before)
- **npm install** for packages on GitHub
- **pip install** for packages hosted externally
- **Hermes web_search** to Google (via SearXNG proxy config)
- **GPT API calls** (api.openai.com is reachable)
- **Docker pull** — still may fail if the Docker registry is blocked; use docker mirrors or download binaries directly

### Git Through Proxy 的 Env Var 差异

git 的内置 TLS 实现（GnuTLS/OpenSSL）与 curl 的 libcurl 在代理变量读取上有区别：

| 工具 | 正确的环境变量 | 行为 |
|------|--------------|------|
| `curl` | `HTTPS_PROXY`, `ALL_PROXY`, `-x` flag | ✅ 都能工作 |
| `git` (push/fetch/clone) | `all_proxy` (小写) + `https_proxy` (小写)，或 `-c http.proxy=` | ✅ GnuTLS 只认小写变体。`HTTPS_PROXY` (大写) 对 git 可能无效 |

**推荐的 git 推送命令：**

```bash
ALL_PROXY=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890 git push origin branch-name

# 或通过 git -c 选项（更可靠）
git -c http.proxy=http://127.0.0.1:7890 -c https.proxy=http://127.0.0.1:7890 push origin branch-name
```

**不要**在 `~/.hermes/.env` 中设置任何 `HTTP_PROXY` 或 `HTTPS_PROXY` 变量（参见 Pitfalls: Proxy-down cascade）。只对单次命令前置。

## Cron/No_Agent Scripts Need Explicit Proxy Vars

Cron jobs (especially `no_agent=True` scripts) run in a **clean shell environment** — no `ALL_PROXY`, `HTTP_PROXY`, or `HTTPS_PROXY` from your interactive shell carry over. If a cron script calls `git fetch`, `hermes update`, or any network operation to GitHub, it will fail with `GnuTLS recv error (-110)` because the proxy isn't set.

### Fix Pattern

Add proxy exports at the top of any no_agent cron script that needs GitHub access:

```bash
#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
export ALL_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
hermes update      # now git fetch through the proxy works
```

**Key detail:** Export ALL THREE vars (`ALL_PROXY` + `HTTP_PROXY` + `HTTPS_PROXY`). Git respects `all_proxy` (lowercase) and `https_proxy`; curl prefers uppercase `HTTPS_PROXY`. Exporting all covers both tools and avoids inconsistency.

### GnuTLS recv error (-110) — Git Through Proxy TLS Teardown

Even with correct proxy vars, `git fetch` through mihomo can fail **intermittently** with:

```
fatal: unable to access 'https://github.com/...': GnuTLS recv error (-110):
The TLS connection was non-properly terminated.
```

**Root cause:** This system's git (2.53.0) uses its own internal HTTP transport
compiled with **GnuTLS** (`libcurl3t64-gnutls`), not libcurl/OpenSSL. System
`curl --version` showing OpenSSL is irrelevant — git doesn't use it. Through
mihomo's proxy, TLS handshakes sometimes get interrupted (connection reuse,
node switching, rate limiting). The global config `http.version=HTTP/1.1` helps
but doesn't eliminate the issue.

**Preferred fix: Switch git's TLS backend to OpenSSL (when available)**

This system has both `libcurl3t64-gnutls` and `libcurl4t64` (OpenSSL flavor)
installed. Setting `GIT_SSL_BACKEND=openssl` switches git's TLS backend
at run time without rebuilding:

```bash
export GIT_SSL_BACKEND=openssl
```

⚠️ **Important:** The git config option `git -c http.sslBackend=openssl` does
**NOT** work on this system — it reports "Unsupported SSL backend 'openssl'.
Supported SSL backends: gnutls". Only the `GIT_SSL_BACKEND` environment
variable works. This is a peculiarity of how Ubuntu's git package resolves
the SSL backend at the process level vs the config level.

**Add to cron/scripts alongside the proxy exports:**

```bash
export ALL_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export GIT_SSL_BACKEND=openssl   # prevents GnuTLS -110
```

**Verify:**
```bash
ALL_PROXY=http://127.0.0.1:7890 GIT_SSL_BACKEND=openssl \
  git fetch --dry-run origin
# Should succeed; without GIT_SSL_BACKEND it may fail intermittently
```

**Fallback: Add retry logic** (use when OpenSSL backend is unavailable):

```bash
MAX_RETRIES=3
RETRY_DELAY=10
for attempt in $(seq 1 $MAX_RETRIES); do
  if [ $attempt -gt 1 ]; then
    echo "→ Retry $attempt/$MAX_RETRIES (waiting ${RETRY_DELAY}s)..."
    sleep $RETRY_DELAY
  fi
  if hermes update; then
    echo "✓ Update successful on attempt $attempt"
    exit 0
  fi
  echo "⚠ Attempt $attempt failed"
done
echo "✗ All $MAX_RETRIES attempts failed."
exit 1
```

**To view the full error (beyond cron watchdog's 240-char truncation):**
```bash
python3 -c "
import json
with open('/home/duruo/.hermes/cron/jobs.json') as f:
    jobs = json.load(f)['jobs']
for j in jobs:
    if j.get('last_status') == 'error':
        print(f'{j[\"name\"]}: {j.get(\"last_error\",\"?\")[:400]}')
"
```
This reads the raw stderr from `jobs.json`. Look for `GnuTLS recv error` to
confirm TLS handshake failure vs other git errors.

### Where to Save the Script

- Runtime location: `~/.hermes/scripts/` — cron scheduler finds scripts here
- Git-tracked backup: `~/src/hermes-agent/scripts/` — prevent drift after `hermes update`
- Apply both: `cp ~/.hermes/scripts/foo.sh ~/src/hermes-agent/scripts/foo.sh`

### Verification

```bash
# Without proxy — should timeout/block:
cd ~/src/hermes-agent && timeout 15 git fetch --dry-run origin

# With proxy exported — should succeed:
export ALL_PROXY=http://127.0.0.1:7890
cd ~/src/hermes-agent && timeout 15 git fetch --dry-run origin
```

## Pitfalls

- **Config format mismatch:** Old Clash configs use `port: 7890` + `socks-port: 7891`. mihomo v1.19+ uses `mixed-port: 7890`. If the proxy starts but doesn't listen on the expected port, this is the most likely cause.
- **mihomo-cli start fails with stale PID:** The `mihomo start` command may fail with `"仍有进程残留"` if a previous instance left a PID behind. Use `kill -9 $(pgrep -f mihomo)` (or manually via the PID shown) to clear it, then start fresh. If sudo is unavailable, `kill -9` works for user-owned processes.
- **No runtime config or log directory:** If `~/.mihomo-cli/runtime/config.yaml` doesn't exist, the kernel config is missing. Run mihomo directly with `-f` pointing to the subscription YAML instead of relying on mihomo-cli to generate it.
- **api.openai.com and chatgpt.com time out through airport nodes:** The OpenAI API endpoint (`api.openai.com/v1/`) and ChatGPT API endpoint (`chatgpt.com/backend-api/`) are both **unreachable** through Lv.2 airport subscription nodes (time out after 5s+, HTTP 000). This affects ALL tested nodes (US, DE, FR, JP, SG, HK) — the VPN provider likely blocks OpenAI/ChatGPT traffic at the infrastructure level. **Contrast** with `auth.openai.com` which returns a Cloudflare JS challenge (HTTP 403) — the OAuth login flow works because Codex CLI uses a real browser. Programmatic API access (model list, completions) via the proxy is blocked. If GPT API access is needed from the NUC, use a different provider or run without proxy.
- **Docker image unavailable:** Docker Hub is typically blocked. mihomo is not available in Docker mirrors either. Use npm-based install.
- **Subscription URL accessible, binary download is not:** The subscription URLs from Chinese providers (23333.moe, etc.) work, but GitHub binary downloads need the `--mirror` flag.
- **NO_PROXY is critical:** Without it, local services on the NUC (SearXNG, Dashboard, Xiaohongshu MCP) will try to route through the proxy and break. Always include `localhost`, `127.0.0.1`, and LAN subnets.
- **Proxy-down cascade breaks Hermes Feishu:** When mihomo stops unexpectedly, the Hermes gateway loses all ability to reach Feishu's API — even though the gateway process stays alive. The lark-oapi SDK proxies ALL API calls (message reactions, file downloads, token refresh) through `HTTP_PROXY`, not just the initial WebSocket handshake. Result: Feishu appears disconnected (`CLOSE-WAIT` TCP state), but gateway looks healthy from systemd. **Prevention:** Add `HTTP_PROXY=''` `HTTPS_PROXY=''` `NO_PROXY=*` to the gateway systemd service file to force direct connectivity. **Recovery:** Start mihomo → `pkill -9 -f 'gateway run'` → `systemctl --user reset-failed hermes-gateway.service && hermes gateway start`. See `hermes-gateway-platforms` skill for full diagnostic details.
- **`external-controller: 9090` (bare port) fails silently:** mihomo interprets a bare number like `9090` as a hostname, not a port. The log shows `ERROR External controller listen error: listen tcp: address 9090: missing port in address`. The REST API at `127.0.0.1:9090` never starts. **Fix:** Use `external-controller: 0.0.0.0:9090` in config.yaml. The API is needed for runtime group switching (see Runtime Management section below).
- **`DOMAIN-KEYWORD,openai` does NOT match `chatgpt.com`:** The `DOMAIN-KEYWORD` rule matches on domain name substrings, and `chatgpt.com` contains no `openai` substring. Codex CLI with ChatGPT Plus OAuth (`auth_mode: chatgpt`) connects to `chatgpt.com/backend-api/wham/apps`, not `api.openai.com` — so it falls through to the catch-all rule instead of the AI service proxy group. In most airport configs this means it hits the default node (often HK) and either times out or gets blocked. **Fix:** Add explicit rules for ChatGPT domains in config.yaml:
  ```yaml
  - DOMAIN-SUFFIX,chatgpt.com,🤖 AI 服务
  - DOMAIN-SUFFIX,oaistatic.com,🤖 AI 服务
  - DOMAIN-SUFFIX,oaiusercontent.com,🤖 AI 服务
  ```
  Then restart mihomo. Even with correct routing, the proxy provider's nodes may still block chatgpt.com at the infrastructure level — runtime testing is essential.
- **Airport "US" nodes may exit in HK:** Some Chinese SSR/SS subscription providers label nodes by routing path rather than actual exit geolocation. Tested 9ss.dev "US01-US06" nodes — all exit at a Hong Kong IP (`151.242.183.54`, PAN-LIAN TECHNOLOGY). Always verify exit IPs before relying on a node for region-locked services (see Node Exit IP Verification below).

## References

- `references/mihomo-setup-2026-06-02.md` — session record of the initial setup, including the exact subscription config fix
- `references/node-exit-ip-verification-2026-06-02.md` — full node exit IP test results for 9ss.dev subscriptions
- `references/node-cloudflare-test-2026-06-02.md` — comprehensive 32-node test against auth.openai.com; confirmed all nodes work for browser-based OAuth (403 is Cloudflare JS challenge, not geo-block)
- `scripts/test_all_nodes.py` — reusable script to batch-test all nodes in a proxy group against any target URL
- `scripts/mihomo_watchdog.sh` — watchdog for auto-restart when mihomo dies (see Mihomo Watchdog section)
