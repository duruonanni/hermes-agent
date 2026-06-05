# Claude Code and Codex CLI Setup with MiMo API

Verified working configuration from real session (2026-06-01).

## Installation (China Workaround)

Both official install scripts are blocked in China:
- claude.ai/install.sh redirects to "App unavailable in region"
- chatgpt.com/codex/install.sh is blocked

Use npm instead (npmjs.org reachable from China):

```bash
npm install -g @anthropic-ai/claude-code
npm install -g @openai/codex
```

## Environment Variables

MiMo has two credential systems with different endpoints:

| Key Type | OpenAI Base URL | Anthropic Base URL |
|----------|----------------|--------------------|
| Pay-as-you-go (`sk-xxx`) | `https://api.xiaomimimo.com/v1` | `https://api.xiaomimimo.com/anthropic` |
| Token Plan (`tp-xxx`) | `https://token-plan-cn.xiaomimimo.com/v1` | `https://token-plan-cn.xiaomimimo.com/anthropic` |

**Crucial rule:** The key prefix (`sk-` vs `tp-`) determines which endpoint to use. A Token Plan key at the pay-as-you-go endpoint returns `Invalid API Key`. A pay-as-you-go key at the Token Plan endpoint returns the same.

### Pay-as-you-go config:
```bash
export ANTHROPIC_BASE_URL=https://api.xiaomimimo.com/anthropic
export ANTHROPIC_API_KEY=sk-your-key-here
export OPENAI_BASE_URL=https://api.xiaomimimo.com/v1
export OPENAI_API_KEY=sk-your-key-here
```

### Token Plan config (verified 2026-06-03):
```bash
export ANTHROPIC_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic
export ANTHROPIC_API_KEY=tp-your-key-here
export OPENAI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
export OPENAI_API_KEY=tp-your-key-here
```

After switching between key types, all four env vars must be updated together. The Hermes .env file should follow the same pattern.

## PATH Issue (SSH Login Shells)

npm -g installed binaries to /home/$USER/.hermes/node/bin/, which is NOT in the default PATH for SSH login shells.

Root cause: ~/.bashrc has [ -z "$PS1" ] && return at the top. When ~/.profile sources it for login shells, it runs in non-interactive mode and returns early.

Fix: Add to ~/.profile (not ~/.bashrc):
```bash
export PATH="$HOME/.hermes/node/bin:$PATH"
```

Then source ~/.profile or re-login.

## Verification

### Claude Code (WORKS)

```bash
claude --model mimo-v2.5-pro -p "say hello in Chinese"
```

The --model flag is required because Claude Code defaults to Anthropic's model names.

### Codex CLI (DOES NOT WORK with MiMo)

Confirmed in session 2026-06-01. Codex CLI cannot use MiMo as a backend.

Attempted approaches that all failed:

- `codex exec --model mimo-v2.5-pro "prompt"` - Shows init output then "ERROR: Reconnecting... 2/5" and times out
- `codex exec --skip-git-repo-check --model mimo-v2.5-pro` - Same reconnect error
- `codex exec --oss --model mimo-v2.5-pro` - Error: only lmstudio/ollama supported in OSS mode
- codex exec --oss --local-provider - OSS mode only supports local providers

Root cause: Codex CLI requires a sandbox/worker backend:
- Normal mode needs ChatGPT OAuth (blocked in China, can't use third-party API)
- OSS mode only supports local model providers (lmstudio, ollama)

MiMo API itself works fine - curl POST to /v1/chat/completions returns HTTP 200.

## Verified Products

| Tool | Format | Works | Notes |
|------|--------|-------|-------|
| Claude Code | Anthropic | Yes | --model flag required |
| Hermes Agent | OpenAI/Anthropic | Yes (built-in) | Native xiaomi provider |
| Codex CLI | OpenAI | No | Sandbox requires ChatGPT OAuth or local OSS |
| Direct curl/SDK | OpenAI | Yes | Raw API calls work |
