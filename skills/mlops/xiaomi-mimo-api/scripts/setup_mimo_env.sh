#!/bin/bash
# 配置 MiMo API Key 到 .env
# 用法: bash scripts/setup_mimo_env.sh

ENV_FILE="$HOME/.hermes/.env"

echo "请输入你的 MiMo API Key（输入内容不会显示在屏幕上）："
read -s API_KEY
echo

if [ -z "$API_KEY" ]; then
    echo "❌ API Key 不能为空"
    exit 1
fi

# 去掉已有的同名行，再追加新的
grep -v '^XIAOMI_API_KEY=' "$ENV_FILE" > "${ENV_FILE}.tmp"
echo "XIAOMI_API_KEY=$API_KEY" >> "${ENV_FILE}.tmp"
mv "${ENV_FILE}.tmp" "$ENV_FILE"

# OpenAI 兼容格式（Codex CLI 用这个）
grep -v '^OPENAI_API_KEY=' "$ENV_FILE" > "${ENV_FILE}.tmp"
echo "OPENAI_API_KEY=$API_KEY" >> "${ENV_FILE}.tmp"
mv "${ENV_FILE}.tmp" "$ENV_FILE"

if ! grep -q '^OPENAI_BASE_URL=' "$ENV_FILE"; then
    echo "OPENAI_BASE_URL=https://api.xiaomimimo.com/v1" >> "$ENV_FILE"
fi

# Claude Code 用 Anthropic 兼容格式
grep -v '^ANTHROPIC_API_KEY=' "$ENV_FILE" > "${ENV_FILE}.tmp"
echo "ANTHROPIC_API_KEY=$API_KEY" >> "${ENV_FILE}.tmp"
mv "${ENV_FILE}.tmp" "$ENV_FILE"

if ! grep -q '^ANTHROPIC_BASE_URL=' "$ENV_FILE"; then
    echo "ANTHROPIC_BASE_URL=https://api.xiaomimimo.com/anthropic" >> "$ENV_FILE"
fi

echo "✅ 已写入 $ENV_FILE"
echo ""
echo "接下来重启 Gateway 让新配置生效："
echo "   hermes gateway restart"
