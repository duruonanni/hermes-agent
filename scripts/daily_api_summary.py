#!/usr/bin/env python3
"""Daily morning summary: DeepSeek balance + MiMo status + live pricing."""
import subprocess, sys, os, json, re, urllib.request, urllib.error, base64
from datetime import datetime

script_dir = os.path.expanduser('~/.hermes/scripts')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S (CST)')
lines = []
lines.append(f"☀️ 早安！API 每日简报 — {now}")
lines.append("")

def run_script(name):
    path = os.path.join(script_dir, name)
    if os.path.exists(path):
        try:
            r = subprocess.run(['python3', path], capture_output=True, text=True, timeout=20)
            out = r.stdout.strip()
            err = r.stderr.strip()
            if out:
                return out
            if err:
                return f"[{name}] Error: {err[:200]}"
            return f"[{name}] No output"
        except subprocess.TimeoutExpired:
            return f"[{name}] Timeout"
        except Exception as e:
            return f"[{name}] Failed: {e}"
    return f"[{name}] Script not found"

# ── Pricing cache ──────────────────────────────────────────────
PRICING_CACHE_PATH = os.path.join(script_dir, 'pricing_cache.json')

def fetch_deepseek_pricing():
    """Parse DeepSeek official pricing page for latest rates."""
    url = 'https://api-docs.deepseek.com/quick_start/pricing'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        # Find the pricing table
        tables = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL)
        result = {'source': 'DeepSeek 官方', 'fetched_at': now, 'models': {}}

        for table in tables:
            table_text = re.sub(r'<[^>]+>', ' ', table)
            table_text = re.sub(r'\s+', ' ', table_text).strip()
            if 'flash' not in table_text.lower() and 'v4' not in table_text.lower():
                continue

            # Find output pricing
            cache_hit_match = re.search(
                r'INPUT TOKENS \(CACHE HIT\).*?\$([\d.]+).*?\$([\d.]+)',
                table_text, re.DOTALL
            )
            cache_miss_match = re.search(
                r'INPUT TOKENS \(CACHE MISS\).*?\$([\d.]+).*?\$([\d.]+)',
                table_text, re.DOTALL
            )
            output_match = re.search(
                r'OUTPUT TOKENS.*?\$([\d.]+).*?\$([\d.]+)',
                table_text, re.DOTALL
            )

            flash_prices = {}
            pro_prices = {}

            if cache_hit_match:
                flash_prices['input_cache_hit'] = cache_hit_match.group(1)
                pro_prices['input_cache_hit'] = cache_hit_match.group(2)
            if cache_miss_match:
                flash_prices['input_cache_miss'] = cache_miss_match.group(1)
                pro_prices['input_cache_miss'] = cache_miss_match.group(2)
            if output_match:
                flash_prices['output'] = output_match.group(1)
                pro_prices['output'] = output_match.group(2)

            if flash_prices:
                result['models']['deepseek-v4-flash'] = flash_prices
            if pro_prices:
                result['models']['deepseek-v4-pro'] = pro_prices

            # Extract note about the 75% discount ending
            for line in table_text.split('.'):
                if 'discount' in line.lower() or 'promotion' in line.lower():
                    result['pro_discount_note'] = line.strip()[:200]

        return result
    except Exception as e:
        return {'error': str(e), 'source': 'DeepSeek 官方', 'fetched_at': now}


def get_pricing():
    """Get pricing with cache. Returns dict with DeepSeek + MiMo pricing."""
    cache = {}
    if os.path.exists(PRICING_CACHE_PATH):
        try:
            with open(PRICING_CACHE_PATH) as f:
                cache = json.load(f)
        except:
            pass

    # Only refresh cache if older than 6 hours
    cache_age_safe = False
    if cache.get('cached_at'):
        try:
            cached_time = datetime.strptime(cache['cached_at'], '%Y-%m-%d %H:%M:%S (CST)')
            cache_age_safe = (datetime.now() - cached_time).total_seconds() < 21600  # 6h
        except:
            pass

    if cache_age_safe and cache.get('deepseek'):
        return cache

    # Fetch fresh
    ds = fetch_deepseek_pricing()
    result = {
        'cached_at': now,
        'deepseek': ds,
    }
    try:
        os.makedirs(os.path.dirname(PRICING_CACHE_PATH), exist_ok=True)
        with open(PRICING_CACHE_PATH, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass
    return result


# ── GPT Plus status via Codex OAuth ─────────────────────────
def check_gpt_status():
    """Check ChatGPT Plus OAuth status from Codex CLI auth.json."""
    auth_path = os.path.expanduser('~/.codex/auth.json')
    if not os.path.exists(auth_path):
        return ["  ⚠️ Codex CLI 未登录 (无 auth.json)"]

    try:
        with open(auth_path) as f:
            auth = json.load(f)
    except Exception as e:
        return [f"  ❌ 读取 auth.json 失败: {e}"]

    id_token = auth.get('tokens', {}).get('id_token', '')
    access_token = auth.get('tokens', {}).get('access_token', '')
    if not id_token:
        return ["  ⚠️ Codex CLI 无 id_token"]

    # Decode id_token JWT for subscription info
    try:
        payload_b64 = id_token.split('.')[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        auth_info = payload.get('https://api.openai.com/auth', {})
        plan = auth_info.get('chatgpt_plan_type', 'unknown')
        active_until = auth_info.get('chatgpt_subscription_active_until', '')
        # Try to get email from access_token
        email = 'unknown'
        if access_token:
            try:
                a_payload_b64 = access_token.split('.')[1]
                a_pad = 4 - len(a_payload_b64) % 4
                if a_pad != 4:
                    a_payload_b64 += '=' * a_pad
                a_payload = json.loads(base64.urlsafe_b64decode(a_payload_b64))
                email = a_payload.get('https://api.openai.com/profile', {}).get('email', 'unknown')
            except Exception:
                pass
        from datetime import datetime, timezone
        if active_until:
            exp = datetime.fromisoformat(active_until.replace('Z', '+00:00'))
            remaining = (exp - datetime.now(timezone.utc)).days
            expiry_str = f"{active_until[:10]} ({remaining} 天)"
        else:
            expiry_str = 'unknown'
    except Exception:
        plan = 'unknown'
        email = 'unknown'
        expiry_str = 'unknown'

    result = []
    result.append(f"  ✅ ChatGPT Plus 已绑定 ({email})")
    result.append(f"  计划: {plan} | 订阅到期: {expiry_str}")
    return result


# ── Codex CLI connectivity ──────────────────────────────────────
def check_codex_status():
    """Run Codex doctor and count recent sessions."""
    result = []
    codex_path = os.path.expanduser('~/.hermes/node/bin/codex')
    if not os.path.exists(codex_path):
        return ["  ⚠️ Codex CLI 未安装"]

    # Doctor connectivity check
    try:
        env = dict(os.environ, HTTPS_PROXY='http://127.0.0.1:7890')
        r = subprocess.run([codex_path, 'doctor', '--json'], capture_output=True,
                           text=True, timeout=45, env=env)
        if r.returncode == 0:
            report = json.loads(r.stdout)
            version = report.get('codexVersion', '?')
            overall = report.get('overallStatus', '?')
            checks = report.get('checks', {})
            ws = checks.get('network.connectivity.ws', {})
            ws_status = ws.get('status', '?')
            result.append(f"  v{version} | 连通性: {'✅' if overall == 'ok' else '❌'} | WS: {ws_status}")
        else:
            result.append(f"  ❌ 检查失败: {r.stderr[:100]}")
    except Exception as e:
        result.append(f"  ❌ 异常: {str(e)[:80]}")

    # Recent sessions
    sess_dir = os.path.expanduser('~/.codex/sessions')
    count = 0
    total_bytes = 0
    if os.path.exists(sess_dir):
        import time
        cutoff = time.time() - 7 * 86400
        for root, dirs, files in os.walk(sess_dir):
            for f in files:
                if f.endswith('.jsonl'):
                    fp = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(fp)
                        if mtime > cutoff:
                            count += 1
                            total_bytes += os.path.getsize(fp)
                    except OSError:
                        pass
    result.append(f"  近7天: {count} 次会话 / {total_bytes/1024/1024:.1f} MB")

    return result


# ── Cursor subscription ────────────────────────────────────────
def check_cursor_status():
    """Check Cursor subscription status from statsig-cache."""
    result = []

    # Check cli-config for auth info
    cli_cfg_path = os.path.expanduser('~/.cursor/cli-config.json')
    if not os.path.exists(cli_cfg_path):
        return ["  ⚠️ Cursor 未配置 (无 cli-config.json)"]

    try:
        with open(cli_cfg_path) as f:
            cfg = json.load(f)
        auth = cfg.get('authInfo', {})
        email = auth.get('email', 'unknown')
        result.append(f"  ✅ Cursor 已登录 ({email})")
    except Exception as e:
        return [f"  ❌ 读取 Cursor 配置失败: {e}"]

    # Read subscription info from statsig-cache
    cache_path = os.path.expanduser('~/.cursor/statsig-cache.json')
    if not os.path.exists(cache_path):
        result.append("  ⚠️ 无订阅信息 (statsig-cache)")
        return result

    try:
        with open(cache_path) as f:
            cache = json.load(f)
        data = json.loads(cache.get('data', '{}'))
        custom = data.get('user', {}).get('custom', {})

        plan = custom.get('stripeMembershipStatus', 'free')
        sub_status = custom.get('stripeSubscriptionStatus', '')
        expires = custom.get('stripeMembershipExpiration', '')

        plan_emoji = {'pro': '💼', 'hobby': '🎯', 'free': '⚪', 'business': '🏢'}
        emoji = plan_emoji.get(plan, '🔌')

        if expires:
            from datetime import datetime, timezone
            exp = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            remaining = (exp - datetime.now(timezone.utc)).days
            expiry_str = f"{expires[:10]} ({remaining} 天)"
        else:
            expiry_str = 'N/A'

        usage_dollars = custom.get('included_usage_dollars', None)
        # Check if there's usage/limit info
        if usage_dollars:
            result.append(f"  {emoji} {plan.title()} | 到期: {expiry_str} | 额度: ${usage_dollars}/月")
        else:
            # Try to get from dynamic configs
            for cfg_id, cfg_val in data.get('dynamic_configs', {}).items():
                if cfg_val.get('group') == 'launchedGroup':
                    val = cfg_val.get('value', {})
                    if val.get('included_usage_dollars'):
                        usage_dollars = val['included_usage_dollars']
                        break
                    if val.get('credit_dollars'):
                        usage_dollars = val['credit_dollars']
                        break
            if usage_dollars:
                result.append(f"  {emoji} {plan.title()} | 到期: {expiry_str} | 额度: ${usage_dollars}/月")
            else:
                result.append(f"  {emoji} {plan.title()} | 到期: {expiry_str}")
    except Exception as e:
        result.append(f"  ⚠️ 解析订阅信息失败: {e}")

    return result


# ── Main logic ─────────────────────────────────────────────────

# 1. GPT Plus status (via Codex OAuth)
gpt = check_gpt_status()
lines.append("")
lines.append("ChatGPT Plus (Codex):")
for l in gpt:
    lines.append("  " + l)

# 1b. Codex CLI status
codex = check_codex_status()
for l in codex:
    lines.append("  " + l)

# 2. DeepSeek balance
ds = run_script('check_deepseek_balance.py')
lines.append("")
lines.append("DeepSeek:")
for l in ds.split('\n'):
    lines.append("  " + l)

# 2. MiMo status
lines.append("")
lines.append("MiMo:")

api_key = None
env_path = os.path.expanduser('~/.hermes/.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith('OPENAI_API_KEY='):
            api_key = line[len('OPENAI_API_KEY='):]
            break

if api_key:
    try:
        req = urllib.request.Request('https://token-plan-cn.xiaomimimo.com/v1/models')
        req.add_header('Authorization', f'Bearer {api_key}')
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
        models = [m['id'] for m in data.get('data', [])]
        lines.append(f"  ✅ API 正常")
    except Exception as e:
        lines.append(f"  ❌ API 异常: {e}")
else:
    lines.append("  ⚠️ 未配置 MiMo API Key")

# 3. Cursor subscription
cursor = check_cursor_status()
lines.append("")
lines.append("Cursor:")
for l in cursor:
    lines.append("  " + l)

# 4. Pricing (dynamically fetched)
lines.append("")
lines.append("定价参考 (动态获取):")

pricing = get_pricing()
ds_p = pricing.get('deepseek', {})

# DeepSeek Flash
flash = ds_p.get('models', {}).get('deepseek-v4-flash', {})
if flash:
    ih = flash.get('input_cache_hit', '0.0028')
    im = flash.get('input_cache_miss', '0.14')
    out = flash.get('output', '0.28')
    # Convert USD to approximate CNY (DeepSeek charges ~¥7.14/$1)
    im_cny = round(float(im) * 7.14, 2)
    out_cny = round(float(out) * 7.14, 2)
    lines.append(f"  DeepSeek V4 Flash: 输入 ¥{im_cny}/M / 输出 ¥{out_cny}/M")
    lines.append(f"     (缓存命中 ${ih}/M · 来源: {ds_p.get('source', 'DeepSeek')})")
else:
    lines.append(f"  DeepSeek V4 Flash: 输入 ¥1.0 / 输出 ¥2.0 / M tokens")
    lines.append(f"     (缓存命中 $0.0028/M)")

# DeepSeek Pro (75% discount ended May 31, permanent lower prices)
pro = ds_p.get('models', {}).get('deepseek-v4-pro', {})
if pro:
    ih = pro.get('input_cache_hit', '0.003625')
    im = pro.get('input_cache_miss', '0.435')
    out = pro.get('output', '0.87')
    im_cny = round(float(im) * 7.14, 2)
    out_cny = round(float(out) * 7.14, 2)
    lines.append(f"  DeepSeek V4 Pro: 输入 ¥{im_cny}/M / 输出 ¥{out_cny}/M")
    lines.append(f"     (折扣已结束 · 来源: {ds_p.get('source', 'DeepSeek')})")
else:
    lines.append(f"  DeepSeek V4 Pro: 输入 ¥3.1 / 输出 ¥6.2 / M tokens")

# MiMo — no pricing details shown (user preference)

# Cache timestamp
lines.append(f"  (价格更新于 {now})")

print('\n'.join(lines))
