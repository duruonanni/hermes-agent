# Token Efficiency Patterns for delegate_task

Consolidated reference for minimizing token consumption when delegating to subagents. Apply these when you have 3+ delegations to make or when a single delegation is likely to be context-heavy.

## Three Knobs

| Knob | Effect | Savings |
|------|--------|---------|
| Pre-read + Summary (方案1) | Read files yourself, send 2-3K summary instead of raw 30K+ | 70-90% inbound |
| Toolset Restriction (方案2) | Subagent can't do web_search/read_file on its own | 10-30% + prevents waste loops |
| readonly=True | Subagent can't write files — forces analysis mode | Prevents accidental write cascades |

## Pattern 1: Pre-read + Summary

```python
# BAD — dump raw files
skill = read_file("skills/X/SKILL.md")  # 8K tokens
code = read_file("src/tools/Y.py")      # 12K tokens
delegate_task(goal="评估方案", context=f"SKILL:\n{skill}\n\nCODE:\n{code}")
# Inbound: ~30K + subagent re-reads ≈ 40-50K

# GOOD — you read, you distill
skill = read_file("skills/X/SKILL.md")
code = read_file("src/tools/Y.py")
summary = f"""
SKILL KEY POINTS:
- {skill[:2000]}  # only critical parts
CODE STRUCTURE:
- Class: Y, key method: process()
- Import hook at line 45
TASK: Evaluate using only this summary.
"""
delegate_task(goal="评估方案", context=summary, toolsets=["_no_tools"])
# Inbound: ~2-3K. Zero tool calls. 90%+ savings
```

## Pattern 2: Toolset Restriction

| Task type | Recommended toolsets | readonly= |
|-----------|-------------------|-----------|
| Pure reasoning (given summary, give conclusion) | `["_no_tools"]` | `True` |
| Code review (read files + judge) | `["file"]` | `True` (auto → file_readonly) |
| Implement code (write + test) | `["terminal", "file"]` | `False` |
| Research (search web) | `["web"]` | `True` |

⚠️ **NEVER use `toolsets=[]`** — it inherits the parent's full toolset (Python falsy trap). Use `["_no_tools"]` (non-existent toolset name → intersection → empty set).

## Combined (Optimal: 90-97% savings)

```python
# 1. Self-read
code = read_file("src/feature/impl.py")
tests = read_file("tests/test_feature.py")

# 2. Distill to 2-3K
summary = f"""IMPLEMENTATION: src/feature/impl.py
- Function: process_data(items)
- Returns: {sorted, grouped}
- Edge cases: null check at line 12, no empty-list check
- Complexity: O(n²) at line 23-30
TESTS: 8 cases, all pass. Missing: empty input test.
TASK: Evaluate code quality, focus on edge cases and performance.
"""

# 3. Send summary only + no tools
delegate_task(
    goal="Review using the pre-read summary below",
    context=summary,
    toolsets=["_no_tools"]
)
# Inbound: 2-3K (vs 74K+). Zero tool calls. Outbound: ~1K.
```

## Effect Comparison

| Configuration | Inbound tokens | Tool calls | Total | Verified |
|--------------|---------------|------------|-------|----------|
| Default (all tools + raw context) | 74,000+ | 16 (5 garbage searches) | 80K+ | ✅ Real data |
| Pattern 1 (summary only) | 8,000 | Same 16 | 14K+ | ✅ Subagent still uses tools |
| Pattern 2 (restrict tools) | 74,000 | 0 garbage | 74K | ❌ `[]` doesn't work |
| **Combined** | **2,000-3,000** | **0** | **3-4K** | ⚠️ Requires `["_no_tools"]` |

## Quick Check (before every delegate_task)

- [ ] Does this subagent need `web_search`?
- [ ] Does it need write access, or just read?
- [ ] Can I pre-read, distill, and send only the summary?
- [ ] Does it need full toolset, or is `["_no_tools"]` enough?
- [ ] Inbound token budget: how much context is appropriate?
