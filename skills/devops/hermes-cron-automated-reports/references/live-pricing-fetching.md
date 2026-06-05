# Live Pricing Fetching for API Reports

## Why

Hardcoded pricing goes stale and produces hallucinations. When MiMo dropped prices 99% on 2026-05-27, the old hardcoded ¥1/¥2 became ¥2 flat (standard) with ¥0.02 cache-hit. DeepSeek V4 Pro exited its 75% discount on 2026-05-31 and permanently lowered prices.

**Rule:** Fetch pricing dynamically from the provider's official page. Cache for 6h. Fall back to cached data on failure.

## Pattern: Agent-Based Cron with Live Pricing

In an agent-based cron job (`no_agent=False`), the script collects live data AND fetches current pricing, then the agent formats the combined output.

```python
# Inside daily_api_summary.py

PRICING_CACHE_PATH = os.path.expanduser('~/.hermes/scripts/pricing_cache.json')

def fetch_deepseek_pricing():
    """Parse DeepSeek official pricing page."""
    url = 'https://api-docs.deepseek.com/quick_start/pricing'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    html = resp.read().decode('utf-8', errors='replace')

    tables = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL)
    result = {'source': 'DeepSeek 官方', 'fetched_at': now, 'models': {}}

    for table in tables:
        table_text = re.sub(r'<[^>]+>', ' ', table)
        table_text = re.sub(r'\s+', ' ', table_text).strip()
        if 'flash' not in table_text.lower() and 'v4' not in table_text.lower():
            continue

        cache_hit = re.search(r'INPUT TOKENS \(CACHE HIT\).*?\$([\d.]+).*?\$([\d.]+)', table_text, re.DOTALL)
        cache_miss = re.search(r'INPUT TOKENS \(CACHE MISS\).*?\$([\d.]+).*?\$([\d.]+)', table_text, re.DOTALL)
        output = re.search(r'OUTPUT TOKENS.*?\$([\d.]+).*?\$([\d.]+)', table_text, re.DOTALL)

        if cache_hit:
            result['models']['deepseek-v4-flash']['input_cache_hit'] = cache_hit.group(1)
            result['models']['deepseek-v4-pro']['input_cache_hit'] = cache_hit.group(2)
        # ... same for cache_miss and output

    return result


def get_pricing():
    """Get pricing with 6h TTL cache."""
    cache = {}
    if os.path.exists(PRICING_CACHE_PATH):
        with open(PRICING_CACHE_PATH) as f:
            cache = json.load(f)

    # Check age
    cache_age_safe = False
    if cache.get('cached_at'):
        cached_time = datetime.strptime(cache['cached_at'], '%Y-%m-%d %H:%M:%S (CST)')
        cache_age_safe = (datetime.now() - cached_time).total_seconds() < 21600  # 6h

    if cache_age_safe and cache.get('deepseek') and cache.get('mimo'):
        return cache  # Use cache

    # Fetch fresh
    result = {
        'cached_at': now,
        'deepseek': fetch_deepseek_pricing(),
        'mimo': fetch_mimo_pricing(),
    }
    with open(PRICING_CACHE_PATH, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result
```

## DeepSeek Pricing Table Structure

The official page at `api-docs.deepseek.com/quick_start/pricing` has ONE pricing table. After stripping HTML tags, the relevant row text is:

```
1M INPUT TOKENS (CACHE HIT) (2)  $0.0028  $0.003625 (75% off (3) ) $0.0145
1M INPUT TOKENS (CACHE MISS)  $0.14  $0.435 (75% off (3) ) $1.74
1M OUTPUT TOKENS  $0.28  $0.87 (75% off (3) ) $3.48
```

Each row has 3 dollar values: Flash / Pro-discounted / Pro-full. The Pro 75% discount ended 2026-05-31 UTC — the "discounted" prices ($0.435 input, $0.87 output) are now permanent.

## USD → CNY Conversion

DeepSeek lists prices in USD. The user's account pays in CNY. The approximate conversion rate is ¥7.14/$1:

| Model | USD (input/output) | Approx CNY |
|-------|--------------------|------------|
| V4 Flash | $0.14 / $0.28 | ¥1.0 / ¥2.0 |
| V4 Pro | $0.435 / $0.87 | ¥3.1 / ¥6.2 |

## MiMo Pricing (Post-May-27 Price Cut)

MiMo does not have a parseable pricing API. Use documented values from the official May 27 announcement:

| Model | Standard (per M tokens) | Cache Hit |
|-------|------------------------|-----------|
| V2.5 | ¥2 | ¥0.02 |
| V2.5 Pro | ¥6 | ¥0.025 |

**Note:** After the May 27 price drop, MiMo no longer distinguishes input/output prices separately or by context window length. Pricing is a flat per-million-tokens rate with optional cache-hit discount. They also introduced Token Plan / Credits billing. The official pricing page is at `https://platform.xiaomimimo.com/pricing` but is a React SPA and cannot be scraped.

## Pitfalls

- **DeepSeek pricing page has one HTML table** with 3 dollar values per row. The regex `OUTPUT.*?\$(\d+.\d+)` will match the word "OUTPUT" in "MAX OUTPUT MAXIMUM: 384K" before reaching the actual pricing row. Always use the full phrase: `INPUT TOKENS \(CACHE HIT\)`, `INPUT TOKENS \(CACHE MISS\)`, `OUTPUT TOKENS`.
- **Cache serialization:** When the script uses `now` for a string timestamp at module level, do NOT reassign `now = datetime.now()` in a local scope — it shadows the outer variable and breaks JSON serialization. Use distinct names like `dt_now`.
- **MiMo pricing page is a React SPA.** The HTML contains no visible pricing text — all prices are rendered client-side. Don't rely on scraping. Use the cached known values from the news announcement and update manually when MiMo announces changes.
- **Neither provider's API models endpoint includes pricing.** `/v1/models` only returns model IDs and ownership info.
