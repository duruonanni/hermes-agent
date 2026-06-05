#!/usr/bin/env python3
"""Sync MEMORY.md and USER.md to a Feishu document."""

import os, sys, json, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
CST = timezone(timedelta(hours=8))

def load_env():
    """Load FEISHU_APP_ID and FEISHU_APP_SECRET from .env file."""
    env = {}
    env_path = os.path.join(HERMES_HOME, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def get_tenant_token(app_id, app_secret):
    """Get Feishu tenant access token."""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())["tenant_access_token"]

def api_request(token, method, path, body=None):
    """Make a Feishu API request."""
    url = f"https://open.feishu.cn/open-apis{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} on {method} {path}: {err_body[:500]}", file=sys.stderr)
        raise

def read_memory_file(filename):
    """Read a memory file, return (char_count, content)."""
    path = os.path.join(HERMES_HOME, "memories", filename)
    if not os.path.exists(path):
        return 0, "(file not found)"
    with open(path) as f:
        content = f.read()
    return len(content), content

def build_children(mem_chars, mem_content, usr_chars, usr_content):
    """Build Feishu document block tree."""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S CST")
    return [
        # Title
        {"block_type": 3, "heading1": {"elements": [{"text_run": {"content": "🧠 Hermes Agent 记忆备份", "text_element_style": {}}}]}},
        # MEMORY.md section
        {"block_type": 4, "heading2": {"elements": [{"text_run": {"content": "MEMORY.md — 环境事实与工具技巧", "text_element_style": {}}}]}},
        {"block_type": 15, "quote": {"elements": [{"text_run": {"content": f"容量: {mem_chars} 字符", "text_element_style": {}}}]}},
        {"block_type": 14, "code": {"elements": [{"text_run": {"content": mem_content, "text_element_style": {}}}], "style": {"language": 1}}},
        # USER.md section
        {"block_type": 5, "heading3": {"elements": [{"text_run": {"content": "USER.md — 用户画像与偏好", "text_element_style": {}}}]}},
        {"block_type": 15, "quote": {"elements": [{"text_run": {"content": f"容量: {usr_chars} 字符", "text_element_style": {}}}]}},
        {"block_type": 14, "code": {"elements": [{"text_run": {"content": usr_content, "text_element_style": {}}}], "style": {"language": 1}}},
        # Footer
        {"block_type": 15, "quote": {"elements": [{"text_run": {"content": f"同步时间: {now}", "text_element_style": {}}}]}},
    ]

def main():
    doc_id = None
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--doc-id":
        doc_id = args[1]

    env = load_env()
    app_id = env.get("FEISHU_APP_ID", "")
    app_secret = env.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("Error: FEISHU_APP_ID/FEISHU_APP_SECRET not found in .env", file=sys.stderr)
        sys.exit(1)

    token = get_tenant_token(app_id, app_secret)

    mem_chars, mem_content = read_memory_file("MEMORY.md")
    usr_chars, usr_content = read_memory_file("USER.md")
    children = build_children(mem_chars, mem_content, usr_chars, usr_content)

    if doc_id:
        # Update existing document
        try:
            existing = api_request(token, "GET", f"/docx/v1/documents/{doc_id}/blocks/{doc_id}/children")
            block_ids = [b["block_id"] for b in existing.get("data", {}).get("items", []) if b.get("block_type") != 1]
            if block_ids:
                api_request(token, "DELETE", f"/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete",
                           {"start_index": 0, "end_index": len(block_ids)})
                print(f"Deleted {len(block_ids)} old blocks")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"Warning: could not read existing doc: {body}", file=sys.stderr)

        api_request(token, "POST", f"/docx/v1/documents/{doc_id}/blocks/{doc_id}/children", {"children": children})
        print(f"Written {len(children)} new blocks")
        print(f"\n🔗 https://bytedance.feishu.cn/docx/{doc_id}")
    else:
        # Create new document
        result = api_request(token, "POST", "/docx/v1/documents",
                            {"title": "🧠 Hermes Agent 记忆备份"})
        new_id = result["data"]["document"]["document_id"]
        api_request(token, "POST", f"/docx/v1/documents/{new_id}/blocks/{new_id}/children", {"children": children})
        print(f"Created new document with {len(children)} blocks")
        print(f"\n🔗 https://bytedance.feishu.cn/docx/{new_id}")

if __name__ == "__main__":
    main()
