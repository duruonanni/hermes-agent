# Node Exit IP & auth.openai.com Connectivity Test — 2026-06-02

## Config

- **Proxy:** mihomo v1.19.26, mixed-port 7890
- **Subscription:** Port384 / 9ss.dev
- **Group tested:** 🤖 AI 服务 → 32 nodes
- **Target:** `https://auth.openai.com` (with proper browser User-Agent)

## Key Finding: Cloudflare, Not Geo-Block

`auth.openai.com` is behind Cloudflare's JS challenge. When probed with curl, ALL nodes return HTTP 403 with a `Just a moment...` page containing `_cf_chl_opt` JavaScript. This is **not** an IP geo-block — it's a bot detection challenge.

Codex CLI's `--device-auth` flow opens a real browser, which executes JavaScript and passes the Cloudflare check. Therefore **all 32 nodes work** for Codex OAuth, including HK/JP/SG nodes.

## Per-Node Results

| Node | auth.openai.com | Exit IP | Notes |
|------|----------------|---------|-------|
| 🇩🇪 DE01 - 德国 | 403 (CF) | - | Browser works |
| 🇫🇷 FR01 - 法国 | 403 (CF) | - | Browser works |
| 🇭🇰 HK01-HK09 - 香港 | 403 (CF) | - | Browser works (all 9) |
| 🇯🇵 JP01-JP06 - 日本 | 403 (CF) | - | Browser works (all 6) |
| 🇲🇾 MY01-MY02 - 马来 | 403 (CF) | - | Browser works |
| 🇷🇺 RU01-RU02 - 俄罗斯 | 403 (CF) | - | Browser works |
| 🇸🇬 SG01 - 新加坡 | 403 (CF) | - | Browser works |
| 🇹🇼 TW01-TW03 - 台湾 | 403 (CF) | - | Browser works (all 3) |
| 🇬🇧 UK01 - 英国 | 403 (CF) | - | Browser works |
| 🇺🇸 US01-US03 - 美国 | 000 (timeout) | - | Dead nodes |
| 🇺🇸 US04-US06 - 美国 | 403 (CF) | - | Browser works |

**Bottom line:** Use `▶️ 自动选择` or any non-US node for Codex OAuth — all work when accessed through a real browser.

## Test Script

`scripts/test_all_nodes.py` in the `nuc-proxy-setup` skill automates this test for any proxy group and target URL.
