# Memory Optimization Review — 2026-06-02

This reference captures the output of the `weekly-memory-optimization-review` cron job,
showing the expected structure, depth, and format of a memory audit report.

**Source:** `~/.hermes/cron/output/667f8448b69f/2026-06-02_17-39-56.md`
**File sizes at time of audit:** MEMORY.md 5,330 bytes | USER.md 2,104 bytes
**Capacity:** memory_char_limit=5000, user_char_limit=2500

---

## Key Findings

### Redundancy (4 groups)

- **A组: DeepSeek non-multimodal + anti-hallucination principle** — Two entries overlapped heavily (both say "DeepSeek API doesn't support image_url"). Merge into one fact + one short principle.
- **B组: Dashboard + Kanban plugin** — Entry #27 was a full expansion of detail already in #25. Delete #27.
- **C组: Docker headless Chrome (4 entries)** — Four entries about same topic. Archive all to skill, keep one short pointer.
- **D组: USER #1 + #9** — Same workflow preference stated twice. Delete USER #9.

### Archive Candidates (skill-covered, safe to delete)

- Feishu WebSocket config → skill:hermes-gateway-platforms
- Gateway restart path → skill:hermes-gateway-platforms
- tesserocr install → skill:ocr-and-documents
- MiMo pricing → skill:xiaomi-mimo-api
- Dashboard + Kanban → skill:hermes-dashboard
- Headless Chrome (4 entries) → skill:headless-chrome-screenshot

### Compression

Approximately 300 chars reclaimable by shortening verbose entries.
Combined with deletions, ~1,900-2,200 chars total freed.

### Capacity Impact

Before: MEMORY.md 5,628/5,000 (+13% over limit)
After (estimated): 3,400-3,700 chars — well under limit

---

## Audit Technique Notes

1. **Compare across both files** — MEMORY.md and USER.md may hold the same fact from different angles. USER.md should hold identity/preferences, MEMORY.md should hold environment facts.
2. **Check all entries for skill coverage** — If a skill was created after the memory entry, the entry is now stale.
3. **Compression first, deletion second** — Always try to preserve information while making it shorter, before deciding to delete.
4. **Don't delete USER.md's cosmetic entries** — User avatar descriptions etc. are low-value but deleting them is noticeable.
