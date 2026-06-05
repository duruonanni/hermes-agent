#!/usr/bin/env python3
"""
Test all nodes in a mihomo proxy group against a target URL.
Used to find which nodes can reach a specific service.

Usage:
    python3 test_all_nodes.py "🤖 AI 服务" "https://auth.openai.com"
    python3 test_all_nodes.py "🐟 漏网之鱼" "https://www.google.com"

Depends on mihomo external-controller at 127.0.0.1:9090 (port 7890 proxy).
"""
import json, urllib.request, subprocess, sys, time

CONTROLLER = "http://127.0.0.1:9090"
PROXY = "http://127.0.0.1:7890"

def get_nodes(group_name):
    encoded = urllib.parse.quote(group_name)
    req = urllib.request.Request(f"{CONTROLLER}/proxies/{encoded}")
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    all_p = data.get("all", [])
    return [p for p in all_p if not p.startswith(("♻️", "🚀", "🎯", "官网", "更新"))]

def switch_node(group_name, node):
    encoded = urllib.parse.quote(group_name)
    req = urllib.request.Request(
        f"{CONTROLLER}/proxies/{encoded}",
        data=json.dumps({"name": node}).encode(),
        method="PUT",
    )
    urllib.request.urlopen(req)

def test_url(url, proxy, timeout=10):
    """Test connectivity through proxy. Returns (http_status_or_error, exit_ip)."""
    try:
        # Get HTTP status
        r = subprocess.run(
            ["curl", "-s", "--connect-timeout", str(timeout//2), "--max-time", str(timeout),
             "-x", proxy, "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        status = r.stdout.strip() or "TIMEOUT"

        # Get exit IP (only if previous step didn't take too long)
        r2 = subprocess.run(
            ["curl", "-s", "--connect-timeout", "5", "--max-time", "8",
             "-x", proxy, "https://httpbin.org/ip"],
            capture_output=True, text=True, timeout=10
        )
        try:
            ip = json.loads(r2.stdout).get("origin", "?")
        except (json.JSONDecodeError, KeyError):
            ip = "?"
    except subprocess.TimeoutExpired:
        status, ip = "TIMEOUT", "?"
    except Exception as e:
        status, ip = f"ERR:{e}", "?"
    return status, ip

def main():
    if len(sys.argv) < 3:
        group = "🤖 AI 服务"
        target = "https://auth.openai.com"
    else:
        group = sys.argv[1]
        target = sys.argv[2]

    nodes = get_nodes(group)
    print(f"Testing {len(nodes)} nodes in '{group}' against {target}")
    print()
    print(f"{'Node':50s} {'Status':10s} {'Exit IP':20s}")
    print("-" * 80)

    for i, node in enumerate(nodes, 1):
        sys.stdout.write(f"\r  [{i}/{len(nodes)}] {node[:40]:40s}")
        sys.stdout.flush()
        try:
            switch_node(group, node)
            time.sleep(1)
            status, ip = test_url(target, PROXY)
        except Exception as e:
            status, ip = f"ERR", str(e)[:18]
        flag = "✅" if status in ("200", "301", "302", "307") else \
               "⚠️" if status not in ("000", "TIMEOUT") else "❌"
        print(f"\r{flag} {node:47s} {status:8s} {ip:20s}")

    print("\n" + "-" * 80)

if __name__ == "__main__":
    main()
