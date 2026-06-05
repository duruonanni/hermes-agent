# USER.md Profile Restructure (2026-06-03)

## Context

User had a GPT-evaluated restructured profile they wanted merged into USER.md. The existing file was ~3,086 chars in `##`-header format (externally edited, causing memory tool drift #26045). Target was a merged version incorporating Task Modes, Verification Loop, and other structured improvements.

## Challenge: Character Limit

USER.md has a **2,500 char total limit** across all entries (configured via `memory.user_char_limit`). The merged profile draft was 4,170 chars — 67% over.

**Solution:** Split across multiple `§`-delimited entries:

| Entry | Content | Chars |
|-------|---------|-------|
| 1 | Core Principle + Task Modes (Level 0-4) + Verification Loop (5-step) | 656 |
| 2 | Behavioral Rules 1-6 (Output, Exploration, Documentation, Feature Discovery, Multi-part, MiMo) | 612 |
| 3 | Behavioral Rules 7-10 + Anti-Patterns + Audit Expectation + Meta | 830 |
| **Total** | | **2,104 / 2,500 (84%)** |

## Workflow

### 1. Handle drift first

The existing USER.md was in `##`-header format (non-`§`), causing memory tool to refuse writes:

```
Refusing to write USER.md: file on disk has content that wouldn't round-trip
```

**Fix:** Remove the drift file, then rebuild via memory tool:

```bash
cp ~/.hermes/memories/USER.md ~/.hermes/memories/USER.md.bak
rm ~/.hermes/memories/USER.md
```

After this, the internal store shows 0/2,500 chars — **the content is not preserved internally**.

### 2. Plan entry sizes

Calculate char counts before writing:

```python
total = sum(len(entry) for entry in entries)
separator_overhead = len("\n§\n") * (len(entries) - 1)
final_total = total + separator_overhead
# Must be <= 2,500 for USER or <= 5,000 for MEMORY
```

### 3. Add entries sequentially

```python
memory(action='add', target='user', content='<entry 1>')
memory(action='add', target='user', content='<entry 2>')
# ...
```

Each `add` appends to the store; the tool handles `§` placement.

### 4. Verify

Check that `memory()` returns show correct usage and entry_count. Also verify the rendered file:

```bash
wc -c ~/.hermes/memories/USER.md
# Validate round-trip
python3 -c "
ENTRY_DELIMITER = '\n§\n'
with open('...') as f:
    raw = f.read()
parsed = [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]
roundtrip = ENTRY_DELIMITER.join(parsed)
ok = raw.strip() == roundtrip
print(f'Round-trip: {ok}, Entries: {parsed}')
"
```

### 5. Sync to Feishu

```bash
python3 ~/.hermes/scripts/sync_memory_to_feishu.py --doc-id IfPldCubnoBqftxbrV6cRPfFn7f
```

## Merged Profile Structure

The final USER.md has 3 entries covering:

- **Core Principle** — correctness, traceability, verified effectiveness
- **Task Modes (Level 0-4)** — Q&A through joint decision with MiMo
- **Verification Loop (5-step)** — root cause → fix → evidence → confirm → risks
- **Behavioral Rules 1-10** — Output Format, Exploration (budgeted), Documentation Strategy, Feature Discovery (6-step), Multi-part Messages, MiMo Collaboration, Web Search Scope, Task Safety, PR Discipline (5 checks), Progress Tracking
- **Anti-Patterns** — 7 items to avoid
- **Audit Expectation** — concrete case listing + root cause analysis
- **Meta Characteristics** — concise dimension table

## Key Lesson

When USER.md is full or near-full, restructuring requires careful char budgeting. The memory tool's `add` operation rejects entries that would exceed the total limit, so you MUST estimate totals before writing. Splitting across multiple entries is the only way to fit more content.
