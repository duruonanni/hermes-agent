# Mihomo (Clash Meta) Proxy Setup for NUC

## Overview

Mihomo (Clash Meta) provides HTTP/SOCKS5 proxy for accessing blocked foreign services
(Google, GitHub, OpenAI API, etc.) from within China. The proxy runs as a systemd user
service (no sudo required) on port 7890 and is NOT a global proxy — only used on demand.

## Installation

### 1. Install mihomo-cli (npm package)

```bash
npm install -g mihomo-cli
```

This installs aliases: `mihomo`, `mhm`, `mh`.

### 2. Install the mihomo kernel

```bash
mihomo kernel --mirror
```

The `--mirror` flag uses a Chinese CDN mirror (v6.gh-proxy.org) to download the
kernel binary since GitHub is blocked. Installs to `~/.mihomo-cli/kernel/mihomo`.

### 3. Add subscription URLs

```bash
mihomo subscription add "<clash_subscription_url>" "<name>"
```

Each subscription is stored as a YAML file in `~/.mihomo-cli/subscriptions/`.

### 4. Fix config format (critical)

The subscription YAML uses old Clash format (`port: 7890` + `socks-port: 7891`).
Mihomo v1.19+ requires `mixed-port: 7890` instead.

Copy and fix the subscription config:

```bash
cp ~/.mihomo-cli/subscriptions/Port384.yaml ~/mihomo/config.yaml
sed -i 's/^port:/mixed-port:/' ~/mihomo/config.yaml
sed -i '/^socks-port:/d' ~/mihomo/config.yaml
```

### 5. Systemd user service (auto-start on boot)

Create `~/.config/systemd/user/mihomo.service`:

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
```

## Usage

### Check status

```bash
systemctl --user status mihomo.service
mihomo status              # Kernel version, active subscription
```

### List subscriptions

```bash
mihomo subscription list   # or: mihomo sub list
```

### Switch active subscription

```bash
mihomo sub use Port556
mihomo sub use Port384
```

After switching, use the subscription's `clean` command to test and prune nodes:

```bash
mihomo sub clean Port556   # Test latency, remove dead nodes, auto-restart
```

### Test current node

```bash
mihomo test                 # Quick connectivity test
mihomo clean               # Test all, clean failures, auto-restart
```

### Update subscription

```bash
mihomo sub update          # Refresh all subscriptions
mihomo sub update Port384  # Refresh one
```

### Web UI

```bash
mihomo ui                  # Default: zash dashboard
mihomo ui dash             # Alternative dashboard
mihomo ui yacd             # Yacd dashboard
```

### Web UI from another device

The subscription config allows LAN access. From another machine on the same
network, open: `http://192.168.31.94:9090/ui` (external-controller port).

## Using the Proxy

### Per-command (recommended)

```bash
curl -x http://127.0.0.1:7890 https://www.google.com
git clone https://github.com/example/repo.git   # exports HTTP_PROXY in .bashrc
```

### Per-session

```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.0.0.0/8,.local
```

### For Hermes providers

Set `HTTP_PROXY` and `HTTPS_PROXY` in `~/.hermes/.env`. The gateway reads
these at startup.

**Note:** Do NOT set global proxy as default. Chinese websites (Baidu, Taobao,
Weibo, etc.) are faster without a proxy. Only use proxy for specific foreign
services.

## Docker Containers Accessing Host Proxy

Docker containers cannot reach `127.0.0.1:7890` on the host. Use the Docker
bridge gateway IP instead:

```bash
docker network inspect bridge | grep Gateway
# Typically: 172.17.0.1
```

In SearXNG's `settings.yml`:

```yaml
outgoing:
  proxies:
    all://:
      - http://172.17.0.1:7890
```

## Related

- `hermes-web-setup` skill: main skill for web search and browser tools
- SearXNG locations: `~/searxng/` (Docker), port 8888
- Xiaohongshu MCP: `~/xiaohongshu-mcp/` (Docker), port 18060
