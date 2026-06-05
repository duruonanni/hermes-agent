# DS Pro Token Waste & Cache Optimization — 2026-06-03

## The Problem

One delegate_task to DS V4 Pro consumed 740K input tokens and 10K output tokens, with zero prefix cache hits. The session lasted 152 seconds across 16 tool calls.

## Root Cause Analysis

### 1. Context was raw, not curated
The context passed to delegate_task included:
- Full MEMORY.md read (~40K chars)
- Unstructured skill content dump
- Web search results (raw, unfiltered)
- Redundant: much of this had already been read by the orchestrator

### 2. Subagent had unrestricted core tools
Despite `toolsets=[]`, the subagent had read_file, web_search, search_files, skill_view as core tools. It used them to:
- Re-read files the orchestrator had already read (waste: ~100K tokens)
- Execute 5 web searches, most returning garbage results (site:github indexing pollution)
- Search the filesystem for irrelevant patterns

### 3. No prefix cache opportunity
DeepSeek prefix caching requires identical conversation prefixes. Each delegate_task spawns a brand-new session with a different system prompt. Cache hit: 0%.

### 4. Redundant reads
The subagent read `memories/MEMORY.md` twice, checked `~/.hermes/MEMORY.md` (empty), and searched `skills/` for patterns the orchestrator had already searched. ~30% of total token consumption was redundant work.

## The Fix

### Pattern: Orchestrator Pre-Consumes, Delegates Summaries

```
Before:   I [dump raw files] → DS Pro [reads files again + searches web]
              Total: 740K tokens, 0 cache hit, 152s

After:    I [read files] → I [curate 2-3K summary] → DS Pro [reason on summary]
              Estimated: 15-20K tokens, ~70% cache hit, <15s
```

### Concrete Rules

1. **Always pre-read.** Before delegate_task, call read_file, search_files, web_search yourself. Never pass `"go read the skill/我记不全了你看吧"`.

2. **Organize as Verified Facts block.** Structure context as:
   ```
   ## 已验证事实
   - item 1 (来源: MEMORY.md §X)
   - item 2 (来源: 终端输出确认)
   
   ## 需要你决策的问题
   > 一句话定义：...
   ```

3. **Remove irrelevant tools.** If the subagent only needs to reason, don't give it web_search or search_files. If analysis-only, state `"analyze only, do NOT use web_search/read_file/search_files"` in the goal.

### Token Economics

| Approach | Input Tokens | Output Tokens | Cache Hit | Cost (DS Pro ¥6/M) |
|----------|-------------|--------------|-----------|-------------------|
| Raw dump | ~740K | ~10K | 0% | ~¥4.5 |
| Curated summary | ~15K | ~5K | ~70% | ~¥0.04 |
| **Savings** | **~98%** | **~50%** | — | **~99%** |
