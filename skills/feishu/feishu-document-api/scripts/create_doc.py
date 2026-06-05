#!/usr/bin/env python3
"""
Feishu Document Creation Script
Full workflow: authenticate → create doc → write blocks → print URL

Usage:
    python3 create_doc.py "文档标题"

Requires:
    FEISHU_APP_ID and FEISHU_APP_SECRET in ~/.hermes/.env
"""

import json, os, sys, urllib.request

# ── Config ──
TITLE = sys.argv[1] if len(sys.argv) > 1 else "示例文档"

def read_env(key):
    env_path = os.path.expanduser('~/.hermes/.env')
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(key + '='):
                return line.split('=', 1)[1]
    return None

APP_ID = read_env('FEISHU_APP_ID')
APP_SECRET = read_env('FEISHU_APP_SECRET')
if not APP_ID or not APP_SECRET:
    print("❌ FEISHU_APP_ID / FEISHU_APP_SECRET not set in ~/.hermes/.env")
    sys.exit(1)

BASE = 'https://open.feishu.cn'

# ── 1. Get tenant access token ──
token_data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
req = urllib.request.Request(
    f'{BASE}/open-apis/auth/v3/tenant_access_token/internal',
    data=token_data, headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req, timeout=15)
token = json.loads(resp.read().decode()).get('tenant_access_token')
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json; charset=utf-8'
}
print(f"✅ Token acquired (expires in ~2h)")

# ── 2. Create document ──
body = json.dumps({"title": TITLE}).encode('utf-8')
req = urllib.request.Request(
    f'{BASE}/open-apis/docx/v1/documents',
    data=body, headers=headers, method='POST'
)
resp = urllib.request.urlopen(req, timeout=15)
doc = json.loads(resp.read().decode())['data']['document']
doc_id = doc['document_id']
print(f"✅ Document created: {TITLE}")
print(f"   ID: {doc_id}")
print(f"   URL: https://bytedance.feishu.cn/docx/{doc_id}")

# ── 3. Write content blocks ──
content = {
    "children": [
        {
            "block_type": 4,
            "heading2": {
                "elements": [{"text_run": {"content": "Section One"}}]
            }
        },
        {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": "This is a paragraph of text."}}]
            }
        },
        {
            "block_type": 12,
            "bullet": {
                "elements": [{"text_run": {"content": "Bullet point A"}}]
            }
        },
        {
            "block_type": 12,
            "bullet": {
                "elements": [{"text_run": {"content": "Bullet point B"}}]
            }
        },
    ]
}

path = f'/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children'
req = urllib.request.Request(
    f'{BASE}{path}',
    data=json.dumps(content, ensure_ascii=False).encode('utf-8'),
    headers=headers, method='POST'
)
resp = urllib.request.urlopen(req, timeout=15)
result = json.loads(resp.read().decode())
print(f"✅ {len(content['children'])} block(s) written")
print(f"📄 {TITLE}")
print(f"   https://bytedance.feishu.cn/docx/{doc_id}")
