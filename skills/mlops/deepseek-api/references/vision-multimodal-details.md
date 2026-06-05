# DeepSeek V4 Vision / Multimodal — ❌ NOT Supported via API

## Important Correction

**DeepSeek V4 Flash and V4 Pro do NOT support image/multimodal input via the API.**

The `content[]` array in chat completions **only accepts** `{"type": "text"}`. Passing `{"type": "image_url"}` returns:

```
unknown variant `image_url`, expected `text`
```

## Timeline — What Actually Happened

| Date | Event | Scope |
|:----:|-------|:-----:|
| 2026-04-24 | DeepSeek V4 (Pro + Flash) released via API | Text-only API. No vision. |
| 2026-05-09 | "识图模式" (image recognition) fully opened | **Web/App only** (chat.deepseek.com). NOT available via API. |

Source of confusion: ZOL article "DeepSeek识图模式全面开放，V4正式迈入多模态新阶段" (2026-05-09) — describes the product feature, not the API capability.

## API Confirmation

```bash
curl https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "hello"},
          {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}}
        ]
      }
    ]
  }'
```

→ Returns error: `unknown variant \`image_url\`, expected \`text\``

## How Hermes Agent Handles Vision

Hermes routes vision through a **separate config block** (`vision.*`), not the main model:

```yaml
# config.yaml — current (correct) configuration
model:
  default: deepseek-v4-flash   # text only
  provider: deepseek
  base_url: https://api.deepseek.com

vision:
  model: mimo-v2-omni          # vision handled by MiMo
  provider: openai
  base_url: https://api.xiaomimimo.com/v1
```

This is the **correct design** — DeepSeek V4 has no vision API, so MiMo fills that role.

## ⚠️ Lesson: Product Feature ≠ API Capability

News articles about "X now supports image recognition" usually refer to the product (website/app). Always check:
1. **API documentation** — does the API endpoint accept `image_url` or `image` type?
2. **Actual API response** — call it and check
3. **The config** — what is actually configured under `vision.*` in config.yaml?

Do NOT assume API-level multimodal support based on product-level announcements.
