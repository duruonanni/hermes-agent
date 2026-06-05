---
name: feishu-document-api
description: >
  Create, write, and manage Feishu (Lark) documents programmatically via the Open API. Covers auth, block-type reference, pitfalls, and complete scripts.
version: 2.3.0
compatibility: Hermes Agent
metadata:
  hermes:
    tags: [feishu, document, API, lark]
    related_skills: [hermes-agent]
    trigger: manual
---

# Feishu Document API

Use when the user asks to create, write to, or manipulate Feishu documents via the Open API.

Merged from: `productivity/feishu-api` (v1.0.0)

## Prerequisites

- `FEISHU_APP_ID` and `FEISHU_APP_SECRET` in `~/.hermes/.env`
- The Feishu app must have the `docx:document` permission enabled in [飞书开放平台](https://open.feishu.cn/app) → 权限管理 → 添加 `docx:document`. 添加后需要发布新版本才能生效.

## Workflow

### 1. Get tenant access token

Two equivalent approaches:

**Option A — `http.client`:**
```python
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

conn = http.client.HTTPSConnection('open.feishu.cn')
tok = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
conn.request('POST', '/open-apis/auth/v3/tenant_access_token/internal', tok, {'Content-Type': 'application/json'})
resp = conn.getresponse()
token = json.loads(resp.read().decode()).get('tenant_access_token')
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=utf-8'}
```

**Option B — `urllib.request`** (avoids `http.client` UTF-8 encoding issues):
```python
import json, urllib.request

# Read env vars similarly...
token_data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=token_data, headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req, timeout=15)
token = json.loads(resp.read().decode()).get('tenant_access_token')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=utf-8'}
```

### 2. Create document

```
POST /open-apis/docx/v1/documents
Body: {"title": "文档标题"}
```

Returns `document_id` — this is also the root block ID.

### 3. Add content blocks

```
POST /open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children
Body: {"children": [...]}
```

### 4. Transfer document ownership (alternative to adding members)

When `permission.member.create` fails (error codes 917813, 1066001), use ownership transfer instead:

```
POST /open-apis/drive/v1/permissions/{token}/members/transfer_owner?type=docx
Body: {"member_type": "openid", "member_id": "<user_open_id>"}
```

**⚠️ HTTP method:** use **POST** not PATCH — PATCH returns 404.

The document `token` is the same as `document_id`. After transfer, the user becomes the document owner with full access including version history.

**⚠️ Critical timing: always transfer BEFORE exposing the link.** The user has no access during the window between creation and transfer. Follow this sequence:

```
1. Create doc → 2. transfer_owner (POST) → 3. verify success response → 4. send link to user
```

If transfer fails, **delete the document** to avoid orphans:
```
DELETE /open-apis/drive/v1/permissions/{token}?type=docx
```

This is the recommended pattern when direct `permission.member:create` is unavailable — verified working. See `references/ownership-transfer.md` for the full Python workflow.

### 5. Read a document

Read existing Feishu documents — no create/write required, same auth token.

**Option A — Raw content (plain text):**

```
GET /open-apis/docx/v1/documents/{document_id}/raw_content
```

Returns a single `content` field with all text concatenated (headings as `#`, bullets as `-`, etc.). Fast and simple for searching or summarising.

**Option B — Structured blocks (full fidelity):**

```
GET /open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children?page_size=500
```

Returns typed blocks — you can identify headings (type 3–7), bullets (12), code (14), quotes (15) and extract `text_run` content per block.

Complete Python example for reading:

```python
import json, urllib.request
from urllib.error import HTTPError

headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
doc_id = "your-document-id"  # last segment of docx URL

# Option A: raw text
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content',
    headers=headers
)
resp = urllib.request.urlopen(req, timeout=15)
raw = json.loads(resp.read().decode())
print(raw['data']['content'])  # plain markdown-like text

# Option B: structured blocks
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children?page_size=500',
    headers=headers
)
resp = urllib.request.urlopen(req, timeout=15)
blocks = json.loads(resp.read().decode())['data']['items']
for block in blocks:
    text = ''
    for key in ['text','heading1','heading2','heading3','heading4','heading5','bullet','ordered','code','quote']:
        if key in block:
            for el in block[key].get('elements', []):
                if 'text_run' in el:
                    text += el['text_run'].get('content', '')
    if text.strip():
        prefix = '#' if block['block_type'] in range(3,8) else '> ' if block['block_type']==15 else ''
        print(f'{prefix} {text}')
```

**Document ID extraction:** The Feishu docx URL format is `https://{tenant}.feishu.cn/docx/{document_id}`. The last path segment is the document ID.

### Block type reference

| block_type | Key | Element type |
|-----------|-----|-------------|
| 1 | `page` | Root block (document itself) |
| 2 | `text` | Normal paragraph |
| 3 | `heading1` | Heading level 1 |
| 4 | `heading2` | Heading level 2 |
| 5 | `heading3` | Heading level 3 |
| 6 | `heading4` | Heading level 4 |
| 7 | `heading5` | Heading level 5 |
| 12 | `bullet` | Bullet point (unordered list) |
| 13 | `ordered` | Numbered list |
| 14 | `code` | Code block (monospace, works via children API) |
| 15 | `quote` | Block quote |

### Element format

Each block needs `elements` array with `text_run` objects:

```python
{
    "block_type": 4,  # heading2
    "heading2": {
        "elements": [{"text_run": {"content": "Section Title"}}]
    }
}
```

Optional `text_element_style` for bold/italic/etc:
```python
{"text_run": {"content": "bold text", "text_element_style": {"bold": True}}}
```

### Sharing URL

Documents can be shared with the URL format:
```
https://bytedance.feishu.cn/docx/{document_id}
```
The `document_id` is returned in the create response. The URL works for any user with access to the app's Feishu tenant.

### 6. Display file content as document blocks

When syncing raw text/markdown files (like MEMORY.md or USER.md) into a Feishu document for readable display, convert the file line-by-line into Feishu blocks:

| Source line | Target block | Notes |
|---|---|---|
| `## Section` | heading2 (type 4) | Strip the `## ` prefix |
| `### Subsection` | heading3 (type 5) | Strip the `### ` prefix |
| `- item` | bullet (type 12) | Strip the `- ` prefix |
| `---` | text (type 2) with `─────` | Dividers (type 16) not creatable via API |
| `**bold text:** rest` | text (type 2) | Strip `**` markers, use `text_element_style: {bold: true}` if needed |
| `\| key \| val \|` | bullet (type 12) as `key: val` | Parse table rows into key-value bullets |
| Raw file content/MEMORY.md/etc. | code block (type 14) | block_code(file_text) — monospace, full file dump |

**Key rules:**
- **Always show full content, never summaries** — users want the raw file visible in the doc, not a "syncs automatically" placeholder
- **Write in order** — delete all existing blocks, then write MEMORY.md content first, then USER.md content. Block order = document order
- **Clean markdown artifacts** — strip `**`, ``` `` ```, and other markdown syntax before writing as Feishu text_run
- **Handle table rows** — skip header and separator lines, parse data rows as `bullet("key: value")`

See `references/markdown-to-feishu-blocks.md` for the complete Python conversion function and error handling.

When you need to **periodically overwrite** a document's content (daily/weekly sync), append new blocks won't work — they accumulate stale content. Instead:

1. `GET` the root block's children to get a count
2. `DELETE /open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete` with `{"start_index": 0, "end_index": N}`
3. `POST` new blocks as normal

See `references/in-place-document-sync.md` for the full pattern, Python code, pitfalls, and the **cron no_agent + bash wrapper pattern** for script parameters.

### Complete working scripts & references

Three resources are available:

- `references/feishu-docx-create-write.md` — copy and modify as needed (original create workflow)
- `references/in-place-document-sync.md` — batch-delete update pattern, cron wrapper, real-world memory sync example
- `scripts/create_doc.py` — Full workflow: authenticate, create doc, write blocks, print URL. Run: `python3 ~/.hermes/skills/feishu/feishu-document-api/scripts/create_doc.py "文档标题"`

### Generating PDFs (HTML → PDF)

For generating PDFs (e.g. from HTML guides), see the **`html-to-pdf` skill** — covers WeasyPrint installation, CJK font setup, and pitfalls.

## Pitfalls

### ⚠️ Feishu Rich Text ≠ Markdown Tables
When creating or delivering content to Feishu conversations (via the gateway), be aware that Feishu's `post` rich text format does **not** support Markdown tables. The gateway's `_build_outbound_payload()` method detects markdown tables via `_MARKDOWN_TABLE_RE` and **falls back to plain `text` mode** — the table renders as raw Markdown syntax.

**User preference:** They want ALL messages delivered as rich text (`post` format). When you need to present tabular/comparison data, use indented lists or key-value pairs instead of `| ... |` Markdown tables:

```
Good (rich text works):
  Item A → value 1
  Item B → value 2

Bad (triggers text fallback):
  | Item | Value |
  |------|-------|
  | A    | 1     |
```

This applies to both Feishu documents (where block-based APIs support tables) and conversational messages (where the gateway handles the conversion). For documents the native block API supports tables — the pitfall is specifically for **messages** sent through the gateway.
Chinese characters in body MUST be encoded as UTF-8 bytes. `http.client` defaults to latin-1:

```python
body_bytes = json.dumps(body, ensure_ascii=False).encode('utf-8')
conn.request('POST', url, body_bytes, h)  # NOT the dict
```

### ⚠️ 50 blocks max per POST request
The API enforces a hard limit of **50 blocks per POST** to `/blocks/{id}/children`. Exceeding it returns `code: 99992402` with `field validation failed — the max len is 50`. Always chunk block arrays into batches:

```python
CHUNK_SIZE = 50
for i in range(0, len(all_blocks), CHUNK_SIZE):
    chunk = all_blocks[i:i+CHUNK_SIZE]
    payload = json.dumps({"children": chunk}).encode('utf-8')
    # POST each chunk separately
```

For in-place sync (delete-all → rewrite), count total blocks before deleting. 111 blocks → 3 batches of 50+50+11.

### ⚠️ Too deep nesting (code 1770005)
Inserting blocks as children of a newly-inserted block creates nested hierarchy. When the nesting depth exceeds ~30 levels, the API returns `code: 1770005, msg: "too deep level in document"`.

**Fix:** Use the SAME parent for all sibling inserts, shifting `index` to control position:

```python
# RIGHT — same parent, all siblings
current_idx = anchor_idx
for block in blocks:
    body = json.dumps({"children": [block], "index": current_idx}).encode()
    post_into(DOC_ID, body)  # always at doc root level
    current_idx += 1
```

**Rule of thumb:** Only nest when you intentionally want sub-blocks (e.g. text under a heading). For appending a flat list of blocks, always insert into the document root (`DOC_ID`) with an incrementing `index`.

### ⚠️ Never insert test blocks into a production doc
When debugging Feishu API calls (testing batch limits, block types, parent restrictions), **do NOT insert test blocks into a shared/production document**. The user sees the garbage before you clean it up — and it disrupts their workflow.

**Do this instead:**
1. Create a throwaway test doc: `POST /open-apis/docx/v1/documents` with title "TEST - delete me"
2. Run all debugging probes against the test doc
3. Delete the test doc when done: `DELETE /open-apis/drive/v1/permissions/{token}?type=docx`

**If you accidentally inserted test blocks into a production doc**, immediately use `batch_delete` to remove them from the parent block:

```python
# Get child count, then delete all
items = children_of(parent_block_id, headers)["data"]["items"]
count = len(items)
body = json.dumps({"start_index": 0, "end_index": count}).encode()
del_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{parent_block_id}/children/batch_delete"
urllib.request.Request(del_url, data=body, headers=h, method="DELETE")
```

### ⚠️ Cannot mix block types in a single batch
The API **rejects** batches containing mixed block types with `code: 1770001, msg: "invalid param"`. All blocks in one POST must be the **same** `block_type`:

```python
# WORKS: all type 2
safe = [{"block_type":2,"text":{"elements":[{"text_run":{"content":"A"}}]}},
        {"block_type":2,"text":{"elements":[{"text_run":{"content":"B"}}]}}]

# FAILS (1770001): mixed types
bad = [{"block_type":2,"text":{"elements":[{"text_run":{"content":"A"}}]}},
       {"block_type":3,"heading3":{"elements":[{"text_run":{"content":"B"}}]}}]
```

**Workaround:** Group blocks by type, batch each type group separately, insert sequentially using the `index` parameter:

```python
by_type = {}
for b in all_blocks:
    by_type.setdefault(b["block_type"], []).append(b)

idx = insert_position
for bt in sorted(by_type.keys()):  # insert in original order
    for chunk in chunks(by_type[bt], 40):
        body = json.dumps({"children": chunk, "index": idx}).encode()
        # POST each chunk
        idx += len(chunk)
```

### ⚠️ Doc root does NOT accept heading blocks via API
When inserting at the document root (`DOC_ID` as parent), only **text blocks (type 2)** succeed. Heading blocks (types 3-7) inserted directly under `DOC_ID` return `code: 1770001`.

This is a **runtime restriction** — heading blocks CAN exist at root level (created via the Feishu editor), they just can't be inserted there via API.

**Workaround:** Insert everything as type-2 text blocks with formatting indicators in the content (e.g., `【Heading】` or `**bold**`), or insert heading blocks as children of an existing heading block rather than the doc root.

### ⚠️ Empty text blocks are rejected
Blocks with an **empty `elements` array** return `code: 1770001`. Every text/heading block must have at least one element with non-empty content:

```python
# FAILS: empty elements
{"block_type":2,"text":{"elements":[]}}

# WORKS: use a single space
{"block_type":2,"text":{"elements":[{"text_run":{"content":" "}}]}}
```

### ⚠️ Markdown tables render as raw pipe text in Feishu documents
When you insert content like `| Col1 | Col2 | Col3 |` as a type=2 (text) block, Feishu renders the pipe characters **literally** — it does NOT auto-convert Markdown table syntax to native Feishu table blocks.

```python
# BAD — shows as raw text: | A | B | C |
{"block_type":2,"text":{"elements":[{"text_run":{"content":"| A | B | C |"}}]}}
```

**Solutions:**

**A — Restructure as formatted text (recommended for simple data):**
Use indentation + bold labels or arrow format:
```
  Label A: value of A
  Label B: value of B
  Item → Description
```

**B — Native Feishu table (block_type=31):**
Feishu supports native table blocks via API, but they require complex nested cell/row structures. Only use for multi-column comparison data.

### ⚠️ All-text fallback pattern (when headings fail in batch)
When batch-inserting at the **document root** (DOC_ID as parent), only type=2 text blocks work reliably. Heading blocks (types 3-7) return 1770001 in batch mode.

**Reliable workaround:** Convert ALL content to type=2 text blocks using formatting conventions:

```python
# Instead of heading3 — use bold text
{"block_type":2,"text":{"elements":[{"text_run":{"content":"Section Title","text_element_style":{"bold":true}}}]}}

# Instead of heading4 — use bold subsection markers
{"block_type":2,"text":{"elements":[{"text_run":{"content":"Phase 1 - Subtitle","text_element_style":{"bold":true}}}]}}

# Instead of bullet lists — use indented text
{"block_type":2,"text":{"elements":[{"text_run":{"content":"  ■ Item with detail"}}]}}

# Instead of pipe tables — use formatted label:value rows
{"block_type":2,"text":{"elements":[
    {"text_run":{"content":"P0-1","text_element_style":{"bold":true}}},
    {"text_run":{"content":": Delete file | 30s"}}
]}}
```

This has been verified to work for batches of up to 50 blocks at the document root level.

### ⚠️ Square brackets `[...]` inside content strings cause Python syntax errors
When constructing block dicts inline in Python scripts, **square brackets inside content strings** (`[user:duro]`, `[key:value]`) can confuse the parser into thinking the `]` closes an outer data-structure bracket, producing `SyntaxError: closing parenthesis ']' does not match opening parenthesis '{'`.

**Fix:** Replace bracket-containing tokens parent-friendly alternatives:
```python
# Bad — triggers SyntaxError
"user:duro / user:raya / global 三段隔离"

# Good
"user:duro / user:raya / global 三段隔离"
```
Or construct block dicts programmatically via helper functions rather than inline literals — the issue only affects file-based inline dicts, not runtime-constructed data.

### ⚠️ Batch delete end_index is exclusive, min value = 1

The `end_index` parameter in `batch_delete` is an **exclusive upper bound** with a minimum value of 1. Unlike Python slicing habits (`end_index = len(block_ids) - 1`), Feishu's API requires `end_index = len(block_ids)`.

```python
# WRONG — Python habit: end_index = len(block_ids) - 1
{"start_index": 0, "end_index": len(block_ids) - 1}
# When block_ids has 1 item, end_index=0 → code 99992402 (min is 1)

# RIGHT — Feishu exclusive: end_index = len(block_ids)
{"start_index": 0, "end_index": len(block_ids)}
# 1 block → end_index=1, deletes block at index 0
```

Tested: `{"start_index": 0, "end_index": 1}` on a document with 1 child → returns `code: 0, success`.

### ⚠️ Block type number MUST match the key name

Each block type's `block_type` number and its corresponding key in the block dict must match. Mismatch returns `code: 1770001, msg: invalid param`.

| block_type | Correct key | Wrong key example |
|------------|-------------|-------------------|
| 3 | `heading1` | `heading2` (type 3 is heading1) |
| 4 | `heading2` | `heading3` (type 4 is heading2) |
| 5 | `heading3` | `heading4` (type 5 is heading3) |
| 6 | `heading4` | any other key |

This is easy to get wrong because it's intuitive to think heading2 = block_type 2, but Feishu starts at type 3 for heading1. Always cross-reference with the block type table above.

### ⚠️ Code blocks: type 14 works, type 17 doesn't via children API

**block_type 17** (code block with language syntax highlighting) returns `code: 1770001, msg: "invalid param"` when created via `POST /children`.

**block_type 14** (code block, inline code style) **DOES work** via the children API. Use:

```python
{
    "block_type": 14,
    "code": {
        "elements": [{"text_run": {"content": "full code or file content"}}]
    }
}
```

Type 14 renders as a monospace-style block in the Feishu document — suitable for displaying raw file content like MEMORY.md, log dumps, or config files.

**Rule of thumb:**
- Displaying raw file content → **block_type 14** (works via children API, monospace)
- Only fall back to type 2 (text blocks) for structured display with headings/bullets
- Type 17 can only be created by updating an existing code block via `PATCH /blocks/{block_id}`

See `references/markdown-to-feishu-blocks.md` for the full conversion pattern.

### ⚠️ Block type 16 (divider) not supported
Divider blocks (block_type=16) cannot be added via the children POST API — they can only exist in documents created through the UI. Skip them.

### ⚠️ Permission 99991672 — Missing document scope
If API returns `code: 99991672` with "docx:document scope required":
→ Go to 飞书开放平台 → 应用 → 权限管理 → 添加 `docx:document` → 发布新版本
→ Wait ~5 min for the new permission to take effect.

### ⚠️ Sharing documents (adding members) requires additional scopes
Creating docs only needs `docx:document`. **Sharing** docs with other users needs:
`docs:permission.member:create` or `drive:drive` (umbrella scope).

Adding members via POST `/open-apis/drive/v1/permissions/{token}/members?type=docx`:
```python
body = json.dumps({
    "member_type": "openid",
    "member_id": user_open_id,
    "role": "editor"   # or "viewer", "full_access"
}).encode()
r = urllib.request.Request(url, data=body, headers=h, method="POST")
```

**Error 1066001 (Internal Error)** on POST means scope was added but NOT published, OR the API itself fails even after publishing for some endpoints:
1. Go to 飞书开放平台 → 应用 → 权限管理 → add `docs:permission.member:create`
2. Go to 版本管理与发布 → 创建新版本 → publish
3. Wait 2-5 min after publish, then retry
Adding scopes without publishing has no effect — the API returns 1066001.

**Error 917813 (`permission.to.create member`)** — even after publishing, this error means the API endpoint for member creation is not available. The working workaround is **ownership transfer** (see section 4 above): transfer the document to the user's open_id instead of adding them as a member. The user becomes the owner and can manually add other collaborators in the UI.

### ⚠️ Proactive document suggestion pattern (聊天主动建议文档)
When chatting with users in Feishu, if the conversation involves **multi-step tasks (≥3 steps), cross-session tracking, or multi-person collaboration**, suggest creating a Feishu document. Do NOT immediately edit MEMORY.md — first evaluate if this is a Skill-worthy workflow. The document should be owned by the person you're chatting with:

```
User confirms → Create doc → transfer_owner (to user's open_id) → verify success → send link
User refuses → Don't suggest again this session
Transfer fails → Delete doc, tell user
```

See `references/ownership-transfer.md` for implementation.

### ⚠️ Built-in feishu_drive_* tools may fail — use Open API as fallback
Hermes provides built-in tools (`feishu_doc_read`, `feishu_drive_add_comment`, `feishu_drive_reply_comment`, etc.) that wrap the Feishu Open API. These tools depend on the gateway's Feishu platform context being fully initialized at startup. If the gateway was restarted recently or the Feishu doc client didn't load, these tools return `"Feishu client not available (not in a Feishu comment context)"`.

**This is not a credential/permission issue** — the credentials (`FEISHU_APP_ID`, `FEISHU_APP_SECRET`) are valid and the scopes are correct. The problem is the gateway-side client object not being instantiated.

**Workaround:** Use the Feishu Open API directly via `terminal`/`execute_code` instead of the built-in tools. The Open API always works as long as credentials are present:

```python
import json, urllib.request, os

# Read credentials from .env
env = {}
with open(os.path.expanduser('~/.hermes/.env')) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k] = v

app_id = env['FEISHU_APP_ID']
app_secret = env['FEISHU_APP_SECRET']

# Get tenant_access_token (valid ~2h)
tok_data = json.dumps({'app_id': app_id, 'app_secret': app_secret}).encode()
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=tok_data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req, timeout=15)
token = json.loads(resp.read().decode())['tenant_access_token']
h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Read document raw content
doc_id = 'your-document-id-here'
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content', headers=h)
resp = urllib.request.urlopen(req, timeout=15)
content = json.loads(resp.read().decode())['data']['content']

# Append blocks at a specific index
blocks = [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "new text"}}]}}]
payload = json.dumps({"children": blocks, "index": 60}).encode('utf-8')
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children',
    data=payload, headers=h, method='POST')
resp = urllib.request.urlopen(req, timeout=15)

# Add a whole-document comment
comment = json.dumps({"content": "{\"text\":\"comment text\"}"}).encode('utf-8')
req = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/comments',
    data=comment, headers=h, method='POST')
resp = urllib.request.urlopen(req, timeout=15)
```

When using the Open API directly, remember:
- Always fetch a fresh token (2h expiry) — do not cache across turns
- Inserting at doc root: heading blocks (types 3-7) return 1770001 — use type 2 text with bold instead
- Group blocks by type to avoid the mixed-type batch restriction (code 1770001)
- The last segment of the Feishu URL `https://{tenant}.feishu.cn/docx/{document_id}` is the doc_id

### ⚠️ Token expiry
Tenant access token expires in ~2 hours. For scripts, always fetch a fresh token.

## File path

Pricing/config edits to `agent/usage_pricing.py` live under the Hermes source (`~/.hermes/hermes-agent/`). Edits to files in the venv package path are lost on `pip install -e .`.
