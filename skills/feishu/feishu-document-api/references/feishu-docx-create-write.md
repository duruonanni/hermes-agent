# Feishu Docx: Create + Write Content (Complete Working Script)

Copy this script and modify the `DOC_ID` and content blocks for your use case.

## Full Script

```python
#!/usr/bin/env python3
"""Create Feishu doc and write content blocks."""
import json, os, http.client

env_path = os.path.expanduser('~/.hermes/.env')
def read_env(k):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(k + '='):
                return line.split('=', 1)[1]
    return None

app_id = read_env('FEISHU_APP_ID')
app_secret = read_env('FEISHU_APP_SECRET')

# Step 1: Get tenant access token
conn = http.client.HTTPSConnection('open.feishu.cn')
tok = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
conn.request('POST', '/open-apis/auth/v3/tenant_access_token/internal',
             tok, {'Content-Type': 'application/json'})
resp = conn.getresponse()
token = json.loads(resp.read().decode()).get('tenant_access_token')
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=utf-8'}

# Step 2: Create document
DOC_TITLE = "My Document Title"
body = json.dumps({"title": DOC_TITLE}).encode('utf-8')
conn.request('POST', '/open-apis/docx/v1/documents', body, h)
resp = conn.getresponse()
result = json.loads(resp.read().decode())
doc_id = result['data']['document']['document_id']
print(f"Created: {doc_id}")
print(f"URL: https://bytedance.feishu.cn/docx/{doc_id}")

# Step 3: Add content blocks
content = {
    "children": [
        {"block_type": 4, "heading2": {"elements": [{"text_run": {"content": "Section Title"}}]}},
        {"block_type": 2, "text": {"elements": [{"text_run": {"content": "Normal paragraph text"}}]}},
        {"block_type": 12, "bullet": {"elements": [{"text_run": {"content": "Bullet point"}}]}},
    ]
}
body_bytes = json.dumps(content, ensure_ascii=False).encode('utf-8')
conn.request('POST', f'/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
             body_bytes, h)
resp = conn.getresponse()
result = json.loads(resp.read().decode())
if result.get('code') == 0:
    print(f"Content added! Revision: {result['data']['document_revision_id']}")
else:
    print(f"Failed: {result.get('msg')}")
```

## Block Type Quick Reference

| block_type | Key | Usage |
|-----------|-----|-------|
| 2 | `text` | Normal paragraph |
| 3 | `heading1` | Page title |
| 4 | `heading2` | Section heading |
| 5 | `heading3` | Subsection |
| 6-11 | `heading4-9` | Deeper levels |
| 12 | `bullet` | Bullet list item |
| 13 | `ordered` | Numbered list item |
| 14 | `code` | Code block |
| 15 | `quote` | Block quote |

## Notes

- Document root block_id = document_id (always)
- Block type 16 (divider) is NOT supported in the children POST endpoint
- Content-Type MUST include `charset=utf-8` for Chinese text
- Body MUST be encoded as UTF-8 bytes (not a dict)
- `document_revision_id` increments on each successful content update
- Tenant token expires in ~2 hours; always fetch fresh
