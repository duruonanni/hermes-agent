# DeepSeek API Pricing & Context Windows

Source: https://api-docs.deepseek.com/zh-cn/quick_start/pricing (verified 2026-06-01)

## Model Comparison

| Feature | deepseek-v4-flash | deepseek-v4-pro |
|---------|:-----------------:|:---------------:|
| Context | 1M | 1M |
| Max output | 384K | 384K |
| Thinking mode | Supported (default) | Supported (default) |
| JSON Output | ✅ | ✅ |
| Tool Calls | ✅ | ✅ |
| Conversation prefix continuation | ✅ | ✅ |
| FIM completion | Non-thinking only | Non-thinking only |
| Concurrency | 2500 | 500 |

## Pricing (per million tokens)

| Item | Flash | Flash (w/cache discount) | Pro | Pro (w/cache discount) |
|------|:-----:|:------------------------:|:---:|:----------------------:|
| Input (cache miss) | ¥1 | ¥0.02 (2% of base) | ¥3 | ¥0.025 (0.8% of base) |
| Input (cache hit) | ¥0.02 | — | ¥0.025 | — |
| Output | ¥2 | — | ¥12 | — |

> "扣减费用 = token 消耗量 × 模型单价"
> Cache discount applies automatically — no code changes needed.

## Context Window Details

- **1M tokens is the native input context** for both Flash and Pro
- No special parameter, model name, or API version needed — standard `deepseek-v4-flash` at `https://api.deepseek.com` already serves 1M
- Max output is 384K tokens (not 1M)
- The KV cache discount applies automatically; price shown as "2.5折" (75% off) for Pro, Flash is 98% off cached portion

## Balance Check (the only programmatic query)

```
GET https://api.deepseek.com/user/balance
Authorization: Bearer sk-...

Response:
{
  "balance_infos": [
    {"currency": "CNY", "total_balance": "69.05"},
    {"currency": "USD", "total_balance": "0.00"}
  ],
  "is_available": true
}
```

## Hermes Config for This Model

```yaml
# ~/.hermes/config.yaml
model:
  default: deepseek-v4-flash
  provider: deepseek
  base_url: https://api.deepseek.com
```

```bash
# ~/.hermes/.env
DEEPSEEK_API_KEY=sk-***
```

## Token Usage Estimation

**⚠️ WARNING: Agent-mode usage invalidates simple chat estimates. See SKILL.md → Agent-Mode Token Burn.**

Based on session hygiene data from a real agent session (401 messages compressed at 09:06 on 2026-06-01):
- Total: ~266,313 tokens across 401 messages
- Average: ~664 tokens per message (input + output combined)
- Compressed to: ~2,643 tokens / 7 messages

### Real-World Agent Session: 2026-06-01

From balance history:
| Time | Balance | Delta |
|------|:-------:|:-----:|
| 00:25 (May 31) | ¥69.05 | — |
| 04:09 (Jun 1) | ¥68.32 | -¥0.73 (overnight) |
| 09:15 (Jun 1) | ¥66.41 | -¥1.91 (morning) |
| **Total** | | **-¥2.64** |

386 API calls in ~5 hours, heavy agent use (tool calls, execute_code, file ops, subagents).
Average cost: ~¥0.007 per API call (mix of cache-hit and cache-miss).

The pricing page shows "2.5折" for the cache-hit rows. This 75% discount is applied to the **base price** (¥1 → ¥0.02 for Flash, ¥3 → ¥0.025 for Pro). DeepSeek applies this automatically when enough prefix matches the cached KV — no opt-in needed.
