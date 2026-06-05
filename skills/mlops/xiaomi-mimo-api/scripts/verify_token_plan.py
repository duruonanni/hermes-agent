#!/usr/bin/env python3
"""
Verify MiMo Token Plan API connectivity.
Tests OpenAI-compatible chat, Anthropic-compatible messages,
deep-thinking (v2.5-pro), and model listing.

Usage: python3 scripts/verify_token_plan.py
"""
import json, os, sys, urllib.request

env_path = os.path.expanduser("~/.hermes/.env")
api_key = ""
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("OPENAI_API_KEY=**            if not api_key:
                api_key = line.split("=", 1)[1].strip().strip("'\"")

if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env")
    sys.exit(1)

prefix = api_key[:8]
print(f"Key found: {prefix}...")
if api_key.startswith("tp-"):
    print("Type: Token Plan")
    base = "https://token-plan-cn.xiaomimimo.com"
else:
    print("Type: Pay-as-you-go")
    base = "https://api.xiaomimimo.com"

oai_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}
anthro_headers = {
    "Content-Type": "application/json",
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
}

errors = 0

def test(name, url, data, hdrs, timeout=30):
    global errors
    try:
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=hdrs, method="POST" if data else "GET")
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode())
        if "models" in url.lower() and not url.endswith("messages"):
            models = [m["id"] for m in result.get("data", [])]
            print(f"  ✅ {name}: {len(models)} models available")
        elif "/messages" in url:
            text = result.get("content", [{}])[0].get("text", "")
            print(f"  ✅ {name}: \"{text[:60]}\"")
        else:
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            r = bool(result.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0))
            print(f"  ✅ {name}: \"{text[:60]}\" (deep thinking: {r})")
    except Exception as e:
        errors += 1
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read().decode()[:200]
            except Exception:
                pass
        print(f"  ❌ {name}: {e}")
        if body:
            print(f"     {body}")

print("\n=== Verification ===")
test("Chat (v2.5)", f"{base}/v1/chat/completions",
     {"model": "mimo-v2.5", "messages": [{"role": "user", "content": "Say hello in 3 words."}], "max_tokens": 20},
     oai_headers)
test("Deep Think (v2.5-pro)", f"{base}/v1/chat/completions",
     {"model": "mimo-v2.5-pro", "messages": [{"role": "user", "content": "What is 2+2? Answer in 1 word."}], "max_tokens": 30},
     oai_headers, timeout=60)
test("Anthropic (Claude Code)", f"{base}/anthropic/v1/messages",
     {"model": "mimo-v2.5", "messages": [{"role": "user", "content": "Say hi back."}], "max_tokens": 30},
     anthro_headers, timeout=45)
test("Models", f"{base}/v1/models", None, oai_headers, timeout=10)

print()
if errors:
    print(f"⚠️  {errors} test(s) failed.")
    sys.exit(1)
else:
    print("✅ All tests passed.")
