# Codex CLI Auth-JWT Monitoring Pattern

## Purpose

Check ChatGPT Plus subscription status via Codex CLI's OAuth tokens — no API key needed. Decodes **both** JWT tokens from `~/.codex/auth.json`:
- **`id_token`** — contains subscription info (`chatgpt_subscription_active_until`, `chatgpt_plan_type`)
- **`access_token`** — contains user profile (`email`), but its `exp` is **token expiry only**

⚠️ **Critical:** Do NOT use `access_token.exp` for subscription expiry — it's the JWT token expiry (~10 days), not the ChatGPT Plus subscription end date.

## Architecture

```
~/.codex/auth.json
  ├── tokens.id_token (JWT)
  │     ├── Decode payload → chatgpt_plan_type, chatgpt_subscription_active_until
  │     └── Sub-key: https://api.openai.com/auth
  └── tokens.access_token (JWT)
        ├── Decode payload → email (https://api.openai.com/profile)
        ├── exp → TOKEN expiry (~10 days) — NOT subscription
        └── (Optional) Use as Bearer → api.openai.com/v1/models
```

**Neither token alone has the full picture — you need both:**
- `id_token` has subscription fields but no email/profile
- `access_token` has email/profile but only token-level expiry

## Code Pattern

```python
import os, json, base64, urllib.request
from datetime import datetime, timezone

def check_gpt_status():
    auth_path = os.path.expanduser('~/.codex/auth.json')
    if not os.path.exists(auth_path):
        return ["⚠️ Codex CLI 未登录 (无 auth.json)"]

    with open(auth_path) as f:
        auth = json.load(f)

    id_token = auth.get('tokens', {}).get('id_token', '')
    access_token = auth.get('tokens', {}).get('access_token', '')
    if not id_token:
        return ["⚠️ Codex CLI 无 id_token"]

    try:
        # Decode id_token for subscription fields
        payload_b64 = id_token.split('.')[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        auth_info = payload.get('https://api.openai.com/auth', {})
        plan = auth_info.get('chatgpt_plan_type', 'unknown')
        active_until = auth_info.get('chatgpt_subscription_active_until', '')

        # Decode access_token for email/profile
        email = 'unknown'
        if access_token:
            try:
                a_payload_b64 = access_token.split('.')[1]
                padding2 = 4 - len(a_payload_b64) % 4
                if padding2 != 4:
                    a_payload_b64 += '=' * padding2
                a_payload = json.loads(base64.urlsafe_b64decode(a_payload_b64))
                email = a_payload.get('https://api.openai.com/profile', {}).get('email', 'unknown')
            except Exception:
                pass

        if active_until:
            exp = datetime.fromisoformat(active_until.replace('Z', '+00:00'))
            remaining = (exp - datetime.now(timezone.utc)).days
            expiry_str = f"{active_until[:10]} ({remaining} 天)"
        else:
            expiry_str = 'unknown'
    except Exception:
        plan = 'unknown'
        email = 'unknown'
        expiry_str = 'unknown'

    return [
        f"✅ ChatGPT Plus 已绑定 ({email})",
        f"计划: {plan} | 订阅到期: {expiry_str}",
    ]
```

## Proxy Handling

If the NUC uses a proxy that blocks OpenAI (common with Chinese airport subscriptions), the API connectivity test will time out. Handle gracefully:

```python
# Optional: test API connectivity through proxy
connected = False
model_count = 0
try:
    proxy = urllib.request.ProxyHandler({'https': 'http://127.0.0.1:7890'})
    opener = urllib.request.build_opener(proxy)
    req = urllib.request.Request('https://api.openai.com/v1/models')
    req.add_header('Authorization', f'Bearer {access_token}')
    resp = opener.open(req, timeout=10)
    models = json.loads(resp.read().decode())
    model_count = len(models.get('data', []))
    connected = True
except Exception:
    pass  # Expected when proxy blocks OpenAI

if connected:
    result.append(f"连通性: ✅ 正常 (可访问 {model_count} 个模型)")
else:
    result.append(f"连通性: ⚠️ API 地址受限 (代理节点未放行)")
```

## JWT Payload Fields

### id_token — contains subscription data
Under the `https://api.openai.com/auth` claim:

| Field path | Example | Meaning |
|---|---|---|
| `chatgpt_plan_type` | plus | Subscription tier (plus/pro/free) |
| `chatgpt_subscription_active_until` | 2026-07-02T09:01:32+00:00 | **True subscription expiry** |
| `chatgpt_subscription_active_start` | 2026-04-.. | Subscription start date |
| `chatgpt_subscription_last_checked` | 2026-06-.. | Last verification timestamp |
| `chatgpt_account_id` | 647fe5f5-... | OpenAI account UUID |
| `chatgpt_user_id` | user-nPkrnaQ... | ChatGPT user ID |

### access_token — contains user profile only
Under the `https://api.openai.com/profile` claim has `email`.
Under `https://api.openai.com/auth` claim may have some fields but **`exp` is always token-level, NOT subscription.**

| Field path | Example | Meaning |
|---|---|---|
| `email` | kate_2012@outlook.com | OAuth account email |
| `exp` | 1781275294 | **Token expiry (~10 days)** — NOT subscription |
| `sub` | auth0\|6696349e... | Auth0 user ID |
| `iss` | https://auth.openai.com | Token issuer |

## Token Lifecycle

- **Access token expiry:** ~10 days from issue (~178 million epoch)
- **id_token fields are stable** — plan type and subscription expiry don't change with each refresh
- **Auto-refresh:** Codex CLI automatically refreshes via `refresh_token` when the access_token is near expiry
- **`last_refresh`** field in auth.json tracks when the token was last refreshed

## Pitfalls

- **Do NOT use `access_token.exp` for subscription expiry.** The access_token's `exp` is always ~10 days from issue. The real subscription expiry is in id_token's `chatgpt_subscription_active_until`. Using access_token.exp shows "Token 到期: 2026-06-12" when the actual subscription expires "2026-07-02".
- **`auth.json` location:** `~/.codex/auth.json`, NOT `~/.config/codex/auth.json` or `~/codex/auth.json`
- **JWT padding:** The base64 payload may need padding (`==` suffix) before `urlsafe_b64decode`
- **Proxy blocking OpenAI:** `api.openai.com` times out through Chinese airport/VPN Lv.2 subscriptions — the token status report should still work (JWT decode doesn't need connectivity)
- **`auth_mode: "chatgpt"`** means OAuth (device-auth), not API key. Don't confuse with `auth_mode: "api_key"`
- **`model_count` unbound variable:** Initialize `model_count = 0` before the try/except block

## Related

- Full implementation in `~/.hermes/scripts/daily_api_summary.py`
- Proxy considerations documented in `nuc-proxy-setup` skill
