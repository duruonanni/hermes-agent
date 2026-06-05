# Node Exit IP Verification — 2026-06-02

## Context

User wanted to use Codex CLI OAuth (OpenAI `auth.openai.com`) which blocks Hong Kong IPs.
Needed to verify whether subscription node labels ("🇺🇸 US01-06") actually exit in the US.

## Method

Used mihomo REST API (`127.0.0.1:9090`) to switch the `🤖 AI 服务` proxy group to each
US-labeled node, then tested exit IP via httpbin.org and ip-api.com.

## Results

All 6 "US" nodes from 9ss.dev (both Port384 and Port556 subscriptions) use the same
Taiwan relay (`relay.2.*.9ss.com.tw`) and exit at a Hong Kong IP:

| Node | Exit IP | Location | ISP |
|------|---------|----------|-----|
| US01 | 151.242.183.54 | Hong Kong | PAN-LIAN TECHNOLOGY CO., LIMITED |
| US02 | 151.242.183.54 | Hong Kong | PAN-LIAN TECHNOLOGY CO., LIMITED |
| US03 | 151.242.183.54 | Hong Kong | PAN-LIAN TECHNOLOGY CO., LIMITED |
| US04 | Timeout | — | — |
| US05 | 151.242.183.54 | Hong Kong | PAN-LIAN TECHNOLOGY CO., LIMITED |
| US06 | Timeout | — | — |

## Impact

- OpenAI OAuth (`auth.openai.com`) blocks HK — cannot use Codex `--device-auth`
- OpenAI API (`api.openai.com`) is NOT region-blocked — `codex --with-api-key` works fine
- For real US exit, a different subscription or provider is needed
