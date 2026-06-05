#!/usr/bin/env python3
"""Generate Analytics HTML snapshot from Hermes state.db.
Outputs hermes_analytics_snapshot.html in the current directory.
No API keys needed — reads state.db directly."""
import sqlite3, os, json
from datetime import datetime

# --- Config ---
RATE = 0.14       # $/1M input (DeepSeek V4 Flash)
RATE_OUT = 0.28   # $/1M output
RATE_CACHE = 0.0028  # $/1M cache read
CNY_PER_USD = 7.25

def q(sql, params=()):
    db = os.path.expanduser('~/.hermes/state.db')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def cost(inp, out, cache):
    return (inp * RATE + out * RATE_OUT + cache * RATE_CACHE) / 1_000_000

def fmt(n):
    if not n: return "0"
    n = int(n)
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)

now = datetime.now()
today_start = int(datetime(now.year, now.month, now.day).timestamp())
cutoff = int(now.timestamp()) - 30 * 86400

# Totals
t = q("SELECT SUM(input_tokens) i,SUM(output_tokens) o,SUM(cache_read_tokens) c,COUNT(*) s,SUM(COALESCE(api_call_count,0)) a FROM sessions WHERE started_at>?", (today_start,))[0]
t30 = q("SELECT SUM(input_tokens) i,SUM(output_tokens) o,SUM(cache_read_tokens) c,COUNT(*) s,SUM(COALESCE(api_call_count,0)) a FROM sessions WHERE started_at>?", (cutoff,))[0]
taa = q("SELECT SUM(input_tokens) i,SUM(output_tokens) o,SUM(cache_read_tokens) c,COUNT(*) s,SUM(COALESCE(api_call_count,0)) a FROM sessions")[0]

# Daily & models
daily = q("SELECT date(started_at,'unixepoch') d,SUM(input_tokens) i,SUM(output_tokens) o,SUM(cache_read_tokens) c,SUM(COALESCE(api_call_count,0)) a,COUNT(*) s FROM sessions WHERE started_at>? GROUP BY d ORDER BY d", (cutoff,))
models = q("SELECT model m,SUM(input_tokens) i,SUM(output_tokens) o,SUM(cache_read_tokens) c,SUM(COALESCE(api_call_count,0)) a,COUNT(*) s FROM sessions WHERE started_at>? AND model IS NOT NULL GROUP BY m ORDER BY SUM(input_tokens)+SUM(output_tokens) DESC", (cutoff,))

daily_json = json.dumps([{'d': r['d'], 'i': r['i'] or 0, 'o': r['o'] or 0} for r in daily])

h = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f1117;color:#e1e4e8;padding:24px}}
.container{{max-width:1200px;margin:0 auto}}
h1{{font-size:24px;margin-bottom:8px}}
.sub{{color:#8b949e;font-size:13px;margin-bottom:24px}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:24px}}
.c{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}}
.l{{font-size:11px;color:#8b949e;text-transform:uppercase}}
.v{{font-size:26px;font-weight:600;margin-top:4px}}
.st{{font-size:13px;color:#8b949e;margin-top:4px}}
.s{{margin-bottom:24px}}
.s h2{{font-size:16px;margin-bottom:12px;color:#f0f6fc}}
.ch{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:8px 10px;color:#8b949e;text-transform:uppercase;border-bottom:1px solid #30363d}}
td{{padding:6px 10px;border-bottom:1px solid #21262d}}
.gn{{color:#3fb950}}
.bl{{color:#58a6ff}}
.pu{{color:#d2a8ff}}
.or{{color:#ffa657}}
</style>
</head>
<body>
<div class="container">
<h1>Hermes Analytics Snapshot</h1>
<p class="sub">{now.strftime("%Y-%m-%d %H:%M")} &middot; DeepSeek V4 Flash &middot; <a href="https://platform.deepseek.com" style="color:#58a6ff">platform.deepseek.com</a></p>

<div class="g">
<div class="c"><div class="l">Today Tokens</div><div class="v">{fmt(t['i']+t['o'])}</div><div class="st">In {fmt(t['i'])} / Out {fmt(t['o'])}</div></div>
<div class="c"><div class="l">Today Cost</div><div class="v gn">${cost(t['i'],t['o'],t['c']):.4f}</div><div class="st">&asymp; &yen;{cost(t['i'],t['o'],t['c'])*CNY_PER_USD:.2f}</div></div>
<div class="c"><div class="l">Today Sessions</div><div class="v">{t['s']}</div><div class="st">{t['a']} API calls</div></div>
<div class="c"><div class="l">30d Cost</div><div class="v pu">${cost(t30['i'],t30['o'],t30['c']):.4f}</div><div class="st">&yen;{cost(t30['i'],t30['o'],t30['c'])*CNY_PER_USD:.2f}</div></div>
<div class="c"><div class="l">All Tokens</div><div class="v">{fmt(taa['i']+taa['o'])}</div><div class="st">In {fmt(taa['i'])} / Out {fmt(taa['o'])}</div></div>
<div class="c"><div class="l">All Cost</div><div class="v or">${cost(taa['i'],taa['o'],taa['c']):.4f}</div><div class="st">&yen;{cost(taa['i'],taa['o'],taa['c'])*CNY_PER_USD:.2f} &middot; {taa['s']} sessions</div></div>
</div>

<div class="s"><h2>Daily Tokens</h2>
<div class="ch"><canvas id="c1" height="80"></canvas></div></div>

<div class="s"><h2>Models (30d)</h2>
<table><tr><th>Model</th><th>Input</th><th>Output</th><th>API</th><th>Sessions</th><th>Cost</th></tr>
{"".join(f"<tr><td>{r['m']}</td><td>{fmt(r['i'])}</td><td>{fmt(r['o'])}</td><td>{r['a']}</td><td>{r['s']}</td><td class=gn>${cost(r['i']or 0,r['o']or 0,r['c']or 0):.4f}</td></tr>" for r in models)}
</table></div>

<div class="s"><h2>Daily Detail (30d)</h2>
<table><tr><th>Date</th><th>Input</th><th>Output</th><th>Total</th><th>API</th><th>Sessions</th></tr>
{"".join(f"<tr><td>{r['d']}</td><td>{fmt(r['i'])}</td><td>{fmt(r['o'])}</td><td><b>{fmt((r['i']or 0)+(r['o']or 0))}</b></td><td>{r['a']}</td><td>{r['s']}</td></tr>" for r in daily)}
</table></div>

<p class="sub" style="margin-top:24px;text-align:center">
Pricing: Input $0.14/1M &middot; Output $0.28/1M &middot; Cache $0.0028/1M (DeepSeek V4 Flash)<br>
Balance: see platform.deepseek.com<br>
Actual cost from balance snapshots: check_balance.py
</p>
</div>
<script>
const d={daily_json};
new Chart(document.getElementById('c1'),{{
type:'bar',
data:{{labels:d.map(x=>x.d.slice(5)),datasets:[
{{label:'Input',data:d.map(x=>(x.i/1000).toFixed(1)),backgroundColor:'#58a6ff',borderRadius:3}},
{{label:'Output',data:d.map(x=>(x.o/1000).toFixed(1)),backgroundColor:'#3fb950',borderRadius:3}}
]}},
options:{{responsive:true,maintainAspectRatio:false,
plugins:{{legend:{{labels:{{color:'#8b949e'}}}}}},
scales:{{x:{{ticks:{{color:'#8b949e'}},grid:{{color:'#21262d'}}}},y:{{ticks:{{color:'#8b949e'}},grid:{{color:'#21262d'}},beginAtZero:true}}}}
}});
</script>
</body>
</html>'''

out = 'hermes_analytics_snapshot.html'
with open(out, 'w') as f:
    f.write(h)
print(f"Written: {out} ({os.path.getsize(out):,} bytes)")
