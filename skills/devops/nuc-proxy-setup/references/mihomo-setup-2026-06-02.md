# mihomo Setup Session — 2026-06-02

## Environment
- NUC8, Ubuntu 26.04 (no sudo for process management)
- Docker Hub blocked, GitHub blocked, Google blocked
- npm registry accessible, Chinese CDNs (gh-proxy.org) accessible
- Two subscription ports: 384 and 556, both from 23333.moe

## Key Discoveries

### Docker doesn't work
Tried `metacubex/mihomo` image — Docker Hub unreachable. Tried mirrors (`docker.1ms.run`, `docker.xuanyuan.me`) — none cache the mihomo image. Final approach: npm install.

### Config format must be fixed
The subscription returns old Clash format (`port: 7890` + `socks-port: 7891`). mihomo v1.19.26 uses `mixed-port: 7890`. Fix by sed/copy.

### mihomo-cli start is buggy
`mihomo start` fails with stale PID detection. Workaround: kill manually, run mihomo binary directly via systemd service.

### Subscription provider info
- Port384: Soft_Cloud_384, 510MB / 128GB used (0.4%), expires 2026-11-28
- Port556: Soft_Cloud_556, same traffic pool
- Active nodes include: DE01, FR01, HK01-03 (SSR, aes-256-cfb)

## Commands Used

```
npm install -g mihomo-cli
mihomo kernel --mirror
mihomo subscription add "https://sub.23333.moe/link/..." "Port384"
mihomo sub use Port384
cp ~/.mihomo-cli/subscriptions/Port384.yaml ~/mihomo/config.yaml
# Edit: port -> mixed-port, remove socks-port
mkdir -p ~/.config/systemd/user/
# Write mihomo.service (see skill body)
systemctl --user daemon-reload && systemctl --user enable mihomo.service
echo "HTTP_PROXY=http://127.0.0.1:7890" >> ~/.hermes/.env
```

## Verification Results
- google.com: 200 (1.0s via proxy)
- github.com: 200 (via proxy)
- api.openai.com: 403 (network OK, needs API key)
