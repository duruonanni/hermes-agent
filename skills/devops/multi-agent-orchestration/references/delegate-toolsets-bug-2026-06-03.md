# delegate_task toolsets=[] Bug — 2026-06-03

## Status: Unfixed in active Hermes version

`toolsets=[]` in `delegate_task()` **does NOT give an empty toolset**. It inherits the parent's full toolset instead.

## The Bug

```python
# Before fix: `if toolsets:` treats [] as falsy → falls through to parent tools
# After fix: `if toolsets is not None:` allows explicit empty list
```

| Call | Current behavior (bug) | Intended behavior |
|------|----------------------|-------------------|
| `toolsets=None` (default) | Inherit parent ✅ | Inherit parent ✅ |
| `toolsets=[]` | Inherit parent ❌ | Empty toolset (zero tools) |
| `toolsets=["terminal"]` | Intersect with parent ✅ | Intersect with parent ✅ |

## Impact

A single `delegate_task(goal="分析任务", toolsets=[])` that was intended to be a zero-tool reasoning subagent actually:
- Inherited 39 core tools from the parent
- Performed 16 tool calls (file reads, web searches, filesystem searches)
- Consumed **1,067,751 input tokens**
- After the fix: **1,942 tokens**, zero tool calls — a **99.8% reduction**

## Workaround (until fix is merged)

**Option 1:** Use a non-existent toolset name to force an empty intersection:
```python
delegate_task(goal="...", toolsets=["_no_such_tool"])
# → parent will intersect ["_no_such_tool"] with available tools → []
# This worked before the bug and still works as a workaround
```

**Option 2:** Pre-read everything yourself and only send curated summaries:
```python
context = "## Verified facts\n(only facts you've read and verified)\n## One question\n(50 words max)"
delegate_task(goal="Analyze based on this context only, do NOT use web_search/read_file", context=context)
# Even with tool inheritance, the subagent doesn't NEED tools if all info is in context
```

## PR Status

| PR | Author | State | Status |
|----|--------|-------|--------|
| **#11279** | @someone | Open | Original fix. P2, 1 commit, 3 files. **Open since Apr 16 (7+ weeks), 0 reviews.** Not merged. |
| **#38165** | @duruonanni | Closed | First attempt. Closed as duplicate of #11279 by @alt-glitch. |
| **#38167** | @duruonanni | Closed | Second attempt (3-line fix). Closed by author after seeing duplicate flag. Has 3 comments including real-world verification data. |
| **#37891** | @duruonanni | Open | Unrelated PR (skills validate). Reviewed but not this bug. |

**Takeaway:** The fix is known, simple (s/`if toolsets:`/`if toolsets is not None:/). But no maintainer has reviewed #11279 in 7+ weeks. The bug persists in all current Hermes releases.
