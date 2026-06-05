# Env Var → Tool Mapping (from `hermes config check`)

## Web Search / Scraping
```
EXA_API_KEY           → web_search, web_extract
PARALLEL_API_KEY      → web_search, web_extract
FIRECRAWL_API_KEY     → web_search, web_extract
TAVILY_API_KEY        → web_search, web_extract
SEARXNG_URL           → web_search
BRAVE_SEARCH_API_KEY  → web_search
```

## Browser Automation
```
BROWSERBASE_API_KEY   → browser_navigate, browser_click
BROWSERBASE_PROJECT_ID → browser_navigate, browser_click
BROWSER_USE_API_KEY   → browser_navigate, browser_click
FIRECRAWL_BROWSER_TTL → browser_navigate, browser_click
AGENT_BROWSER_ENGINE  → browser_navigate, browser_snapshot
CAMOFOX_URL           → browser_navigate, browser_click
```

## How to verify
```bash
hermes config check
```
Lines of the form `○ ENV_VAR → tool_name` mean: if ENV_VAR is set, tool_name becomes available. A leading `✓` means it's already set, `○` means it's unset (but optional — only needed if you want that tool).

## Debugging quick reference
1. `hermes tools list` — check if toolset is enabled
2. `hermes config check` — check if env vars are set
3. If toolset is ✓ but no tools appear → missing env var
4. Set env var in `~/.hermes/.env`, then `/reset`
