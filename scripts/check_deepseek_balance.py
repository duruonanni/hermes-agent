#!/usr/bin/env python3
"""Check DeepSeek account balance and usage summary via API."""
import os, json, urllib.request, urllib.error
from datetime import datetime

ENV_PATH = os.path.expanduser('~/.hermes/.env')
BALANCE_URL = 'https://api.deepseek.com/user/balance'
USAGE_URL = 'https://api.deepseek.com/user/top_up_log'
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def load_api_key():
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith('DEEPSEEK_API_KEY='):
                return line[len('DEEPSEEK_API_KEY='):]
    return None

def fetch_json(url, api_key):
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('Accept', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ''
        return {'error': f'HTTP {e.code}: {body[:200]}'}
    except Exception as e:
        return {'error': str(e)[:200]}

api_key = load_api_key()
if not api_key:
    print('DEEPSEEK_API_KEY 未配置')
    exit(0)

# Balance
balance = fetch_json(BALANCE_URL, api_key)
if 'error' in balance:
    print(f'❌ 余额查询失败: {balance["error"]}')
    exit(0)

available = balance.get('is_available', False)
infos = balance.get('balance_infos', [])
cny_info = next((b for b in infos if b.get('currency') == 'CNY'), None)

if cny_info:
    total = cny_info.get('total_balance', 'N/A')
    granted = cny_info.get('granted_balance', '0.00')
    topped_up = cny_info.get('topped_up_balance', '0.00')
    print(f'✅ API 正常')
    print(f'   余额: ¥{total} (充值 ¥{topped_up} / 赠送 ¥{granted})')
else:
    print(f'✅ API 正常')
    print(f'   余额: ¥{total}' if cny_info else f'   状态: {"可用" if available else "不可用"}')

print(f'   (查询时间: {now})')
