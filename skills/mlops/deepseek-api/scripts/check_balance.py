#!/usr/bin/env python3
"""Query DeepSeek API balance, save to history, report change from last check.

Usage:
    python3 scripts/check_balance.py

Output:
    ¥66.41 (¥0.00 since last check)
    or
    ¥66.41 (-¥1.91 since last check)

History file: deepseek_balance_history.json (sibling of this script).
"""
import json, os, urllib.request
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..',
    'scripts', 'deepseek_balance_history.json')
HISTORY_FILE = os.path.abspath(HISTORY_FILE)
ENV_PATH = os.path.expanduser('~/.hermes/.env')

def read_api_key():
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith('DEEPSEEK_API_KEY='):
                return line.split('=', 1)[1]
    raise RuntimeError('DEEPSEEK_API_KEY not found in ~/.hermes/.env')

def query_balance(api_key):
    req = urllib.request.Request('https://api.deepseek.com/user/balance')
    req.add_header('Authorization', f'Bearer {api_key}')
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
    for b in data.get('balance_infos', []):
        if b['currency'] == 'CNY':
            return float(b['total_balance'])
    raise RuntimeError('CNY balance not found in response')

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def main():
    api_key = read_api_key()
    balance = query_balance(api_key)
    history = load_history()

    last_balance = history[-1]['CNY'] if history else balance
    delta = balance - last_balance

    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'CNY': balance,
        'delta_from_previous': round(delta, 2),
    }
    history.append(entry)
    save_history(history)

    if delta != 0:
        sign = '+' if delta > 0 else ''
        print(f'¥{balance:.2f} ({sign}¥{delta:.2f} since last check)')
    else:
        print(f'¥{balance:.2f} (¥0.00 since last check)')

if __name__ == '__main__':
    main()
