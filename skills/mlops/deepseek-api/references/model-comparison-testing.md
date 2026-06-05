# V4 Pro vs V4 Flash: Comparison Testing

Methodology for comparing DeepSeek V4 Pro and V4 Flash on the same task.

## Why Compare

- **V4 Flash** (¥1 input / ¥2 output per M tokens) is the default daily driver — fast, cheap, good general reasoning
- **V4 Pro** (¥3 input / ¥12 output per M tokens) offers deeper reasoning for complex tasks — code review, architecture decisions, math proofs
- The user may want to test both before committing to one or switching per task

## Testing Script Pattern

```python
import json, urllib.request, os

env_path = os.path.expanduser("~/.hermes/.env")
api_key = ""
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "DEEPSEEK_API_KEY" in line:
            api_key = line.split("=", 1)[1].strip().strip("'\"")

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + api_key
}

question = "<the test question to compare>"

for model, label in [("deepseek-v4-pro", "V4 PRO"), ("deepseek-v4-flash", "V4 FLASH")]:
    print(f"\n=== {label} ===")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 4000
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps(payload).encode(), headers=headers
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
    msg = resp["choices"][0]["message"]
    usage = resp.get("usage", {})
    rt = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
    print(f"Tokens: {usage.get('total_tokens','?')} total | reasoning: {rt}")
    print(f"Answer: {msg['content'][:500]}")
```

## Metrics to Compare

| Metric | What it tells you |
|--------|-------------------|
| Reasoning tokens | How much the model "thinks" before answering |
| Total tokens | Total cost of the response |
| Output quality | Is the answer more structured, complete, accurate? |
| Response time | Pro typically takes 30-60s, Flash is faster |

## Real Session Data (2026-06-03)

### Logic puzzle (3-box fruit problem):
- **V4 Pro**: 1,460 total / 991 reasoning — structured with numbered steps
- **V4 Flash**: 1,854 total / 1,619 reasoning — more concise conclusion

### Classic puzzle (100-household mad dog, 8-day deduction):
- **V4 Pro**: 1,631 total / 881 reasoning — full mathematical induction
- **V4 Flash**: 736 total / 471 reasoning — concise, same correct answer

**Key insight:** For straightforward logical deduction, both models reach the correct answer. Pro is more pedagogical; Flash is more concise. The difference is most visible on tasks requiring multi-step reasoning chains where intermediate steps matter (code refactoring, architecture trade-offs).

## When to Use Pro vs Flash

| Task Type | Recommended |
|-----------|-------------|
| Daily chat, Q&A, simple code | Flash (cheaper, fast, sufficient) |
| Code review, refactoring, debugging | Pro (deeper reasoning, catches edge cases) |
| Architecture decisions, design docs | Pro |
| Quick lookups, data extraction | Flash |
| Cross-provider evaluation | Both (Flash as primary, Pro as second opinion) |

## Switching

```bash
hermes config set model.default deepseek-v4-pro   # switch to Pro
hermes config set model.default deepseek-v4-flash  # switch back to Flash
```

Requires `/new` or `/reset` to take effect.
