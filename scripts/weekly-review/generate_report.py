#!/usr/bin/env python3
"""
Weekly Review HTML Report Generator
Reads Phase 1 JSON data + skills + memories → generates self-contained HTML report.

Usage:
  # Full generation (reads JSON, scans skills, reads memories, produces HTML)
  python3 generate_report.py --json data/weekly_data_2026-07-07.json --output output/report.html

  # With LLM-provided analysis sections (from agent cron)
  python3 generate_report.py --json data/weekly_data.json --output output/report.html \\
    --topics topics.json --skill-audit audit.json --memory-review review.json
"""

import json
import os
import sys
import re
import argparse
import hashlib
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any
from collections import Counter, defaultdict


# ─── Paths ─────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.expanduser('~/.hermes/skills')
MEMORIES_DIR = os.path.expanduser('~/.hermes/memories')

# ─── Utility: scan skills ──────────────────────────────────────────────

def scan_skills() -> dict:
    """Scan ~/.hermes/skills/ for complete skill inventory."""
    skills = {}
    if not os.path.exists(SKILLS_DIR):
        return skills

    for root, dirs, files in os.walk(SKILLS_DIR):
        if 'SKILL.md' in files:
            skill_path = os.path.join(root, 'SKILL.md')
            rel = os.path.relpath(root, SKILLS_DIR)
            try:
                with open(skill_path) as f:
                    content = f.read(5000)
                # Parse frontmatter
                name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
                desc_match = re.search(r'^description:\s*(.+?)(?:\n\s{2,}|\n[a-z])', content, re.MULTILINE)
                version_match = re.search(r'^version:\s*(.+)$', content, re.MULTILINE)
                skill_name = name_match.group(1).strip().strip('"') if name_match else os.path.basename(root)
                skill_desc = desc_match.group(1).strip().strip('"').strip('>').strip() if desc_match else ''
                skill_version = version_match.group(1).strip().strip('"') if version_match else ''

                # Simplify description - take first line
                skill_desc = skill_desc.split('\n')[0][:120]

                size = os.path.getsize(skill_path)
                skills[skill_name] = {
                    'name': skill_name,
                    'path': rel,
                    'description': skill_desc,
                    'version': skill_version,
                    'size': size,
                    'category': rel.split('/')[0] if '/' in rel else 'root',
                }
            except Exception:
                pass

    return skills


def read_memory_stats() -> dict:
    """Read MEMORY.md and USER.md, return stats."""
    result = {'memory': {}, 'user': {}}
    for key, fname in [('memory', 'MEMORY.md'), ('user', 'USER.md')]:
        path = os.path.join(MEMORIES_DIR, fname)
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            lines = content.strip().split('\n')
            chars = len(content)
            # Count §-delimited entries
            entries = [e.strip() for e in content.split('\n§\n') if e.strip()]
            section_count = len([l for l in lines if l.startswith('== ') and l.endswith(' ==')])

            # Detect long entries (>300 chars)
            long_entries = []
            for e in entries:
                if len(e) > 300:
                    first_line = e.split('\n')[0][:80]
                    long_entries.append({'preview': first_line, 'length': len(e)})

            # Check for mixed-language entries
            mixed = []
            for i, e in enumerate(entries):
                has_cn = bool(re.search(r'[\u4e00-\u9fff]', e))
                has_en = bool(re.search(r'[a-zA-Z]{20,}', e))
                if has_cn and has_en:
                    mixed.append({'index': i, 'preview': e[:60]})

            result[key] = {
                'lines': len(lines),
                'chars': chars,
                'entries': len(entries),
                'sections': section_count,
                'long_entries': long_entries,
                'mixed_lang_entries': mixed,
            }
    return result


def analyze_topics(data: dict) -> dict:
    """Heuristic topic categorization from session titles and user messages."""
    categories = defaultdict(list)
    topics = []

    category_keywords = {
        '运维/基础设施': ['cron', 'gateway', 'mihomo', 'searxng', '代理', 'proxy', 'docker',
                    'immich', 'nuc', '服务器', 'server', '更新', 'update', '部署', 'deploy',
                    '安装', '备份', 'immich', '照片', 'photo'],
        '开发/AI工具': ['codex', 'claude', 'cursor', 'mimo', 'skill', 'agent', 'prompt',
                    'token', '模型', 'model', 'api', 'tool', '调试', 'debug'],
        '飞书/消息': ['飞书', 'feishu', '简报', 'briefing', '推送', 'push', '格式', '消息',
                    '消息', 'format', '99992402'],
        '个人/效率': ['沟通', '建议', '效率', '回复', '离线', '论文', 'paper'],
        '求职/文档': ['简历', 'resume', '求职', '面试', '合同', '文档', '证明', '合同'],
        '硬件/NUC': ['NUC', 'm2', '硬盘', 'ssd', '笔记本', '插槽', '硬件'],
        '调研/学习': ['调研', '数据集', '工具', '推荐', '对比', '分析', 'AI标书', '定损'],
    }

    for s in data['sessions']:
        title = s.get('title', '')
        user = s.get('user', 'unknown')
        messages = s.get('user_messages', [])

        # Determine category from title + messages
        combined = title + ' ' + ' '.join(messages[:3])

        best_cat = '其他'
        best_score = 0
        for cat, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in combined.lower())
            if score > best_score:
                best_score = score
                best_cat = cat

        topic = {
            'session_id': s['id'],
            'title': title,
            'user': user,
            'category': best_cat,
            'messages': s['message_count'],
            'tokens': (s.get('input_tokens', 0) + s.get('output_tokens', 0)),
            'tool_calls': s.get('tool_calls', 0),
            'user_msg_preview': messages[0][:100] if messages else '',
        }
        topics.append(topic)
        categories[best_cat].append(topic)

    # Generate category summaries
    cat_summaries = {}
    for cat, items in categories.items():
        cat_summaries[cat] = {
            'count': len(items),
            'total_messages': sum(i['messages'] for i in items),
            'total_tokens': sum(i['tokens'] for i in items),
            'items': items,
        }

    return {
        'topics': topics,
        'categories': dict(cat_summaries),
    }


def cross_reference_skills(data: dict, skills: dict) -> dict:
    """Cross-reference skill usage from data with full skill inventory."""
    data_skills = data.get('skills_mentioned', {})
    all_skill_names = set(skills.keys())
    used_names = set(data_skills.keys())

    # Used skills
    used = {name: {'count': count, 'info': skills.get(name, {})}
            for name, count in data_skills.items()}

    # Unused skills (in inventory but not used this week)
    unused = sorted(all_skill_names - used_names)

    # Unknown skills (used but not in inventory — should be rare)
    unknown = sorted(used_names - all_skill_names)

    # Top 10 most used
    top_used = sorted(used.items(), key=lambda x: -x[1]['count'])[:10]

    # Skills with no calls this week → potential cleanup candidates
    # Skills that were called frequently → core skills

    return {
        'used': {k: v for k, v in used.items()},
        'unused': unused,
        'unknown': unknown,
        'top_used': [(name, info) for name, info in top_used],
        'total_skills': len(skills),
        'total_used': len(used),
        'usage_rate': round(len(used) / max(len(skills), 1) * 100, 1),
    }


# ─── HTML Template ─────────────────────────────────────────────────────

CSS = """
:root {
  --bg: #0d1117;
  --bg-card: #161b22;
  --bg-elevated: #1c2129;
  --border: #30363d;
  --text: #e6edf3;
  --text-dim: #8b949e;
  --text-bright: #f0f6fc;
  --accent: #58a6ff;
  --accent-dim: #1f6feb;
  --green: #3fb950;
  --green-bg: rgba(63,185,80,0.15);
  --yellow: #d29922;
  --yellow-bg: rgba(210,153,34,0.15);
  --red: #f85149;
  --red-bg: rgba(248,81,73,0.15);
  --purple: #a371f7;
  --purple-bg: rgba(163,113,247,0.15);
  --orange: #db6d28;
  --radius: 8px;
  --radius-sm: 4px;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
}

* { margin:0; padding:0; box-sizing:border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px;
}

/* Header */
.header {
  text-align: center;
  padding: 40px 20px 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
.header h1 {
  font-size: 2rem;
  color: var(--text-bright);
  margin-bottom: 4px;
}
.header .subtitle {
  color: var(--text-dim);
  font-size: 0.9rem;
}
.header .window-badge {
  display: inline-block;
  margin-top: 12px;
  padding: 4px 16px;
  background: var(--accent-dim);
  color: var(--text-bright);
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

/* Section */
.section {
  margin-bottom: 40px;
}
.section-title {
  font-size: 1.25rem;
  color: var(--text-bright);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title .icon { font-size: 1.4rem; }

/* Stat Cards Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
}
.stat-card .value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-bright);
  font-family: var(--font-mono);
}
.stat-card .label {
  color: var(--text-dim);
  font-size: 0.85rem;
  margin-top: 4px;
}
.stat-card.highlight {
  border-color: var(--accent-dim);
  background: var(--bg-elevated);
}

/* User Comparison */
.user-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}
.user-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}
.user-card h3 {
  font-size: 1.1rem;
  color: var(--text-bright);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-card .user-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.user-card .mini-stat {
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.user-card .mini-stat .num {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-bright);
  font-family: var(--font-mono);
}
.user-card .mini-stat .lbl {
  font-size: 0.78rem;
  color: var(--text-dim);
}

/* Bar comparison */
.bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 0.85rem;
}
.bar-row .bar-label {
  width: 100px;
  text-align: right;
  color: var(--text-dim);
  flex-shrink: 0;
}
.bar-row .bar-track {
  flex: 1;
  height: 22px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
}
.bar-row .bar-fill {
  height: 100%;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
  min-width: 30px;
  font-family: var(--font-mono);
}
.bar-row .bar-fill.duruo { background: var(--accent-dim); }
.bar-row .bar-fill.raya { background: var(--green); }
.bar-row .bar-fill.green { background: var(--green); }
.bar-row .bar-fill.yellow { background: var(--yellow); }
.bar-row .bar-fill.red { background: var(--red); }

/* Topic Table */
.topic-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.topic-table th {
  text-align: left;
  padding: 10px 14px;
  font-size: 0.8rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}
.topic-table td {
  padding: 10px 14px;
  font-size: 0.88rem;
  border-bottom: 1px solid var(--border);
}
.topic-table tr:last-child td { border-bottom: none; }
.topic-table tr:hover td { background: var(--bg-elevated); }
.topic-table .cat-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.72rem;
  font-weight: 600;
}
.cat-运维 { background: var(--accent-dim); color: #fff; }
.cat-开发 { background: var(--purple-bg); color: var(--purple); }
.cat-飞书 { background: var(--green-bg); color: var(--green); }
.cat-个人 { background: var(--yellow-bg); color: var(--yellow); }
.cat-求职 { background: var(--orange); color: #fff; }
.cat-硬件 { background: var(--red-bg); color: var(--red); }
.cat-调研 { background: var(--purple-bg); color: var(--purple); }
.cat-其他 { background: var(--border); color: var(--text-dim); }

/* Skill Cards */
.skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.skill-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
}
.skill-card .skill-name {
  font-weight: 600;
  color: var(--text-bright);
  font-size: 0.95rem;
}
.skill-card .skill-count {
  float: right;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--accent);
  background: var(--accent-dim);
  padding: 1px 8px;
  border-radius: 10px;
  color: #fff;
}
.skill-card .skill-desc {
  font-size: 0.82rem;
  color: var(--text-dim);
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Alert Box */
.alert {
  padding: 14px 18px;
  border-radius: var(--radius);
  margin-bottom: 16px;
  font-size: 0.9rem;
  line-height: 1.5;
}
.alert-info { background: rgba(88,166,255,0.1); border-left: 3px solid var(--accent); }
.alert-warn { background: var(--yellow-bg); border-left: 3px solid var(--yellow); }
.alert-tip { background: var(--green-bg); border-left: 3px solid var(--green); }

.alert-title {
  font-weight: 700;
  margin-bottom: 4px;
  font-size: 0.9rem;
}
.alert-info .alert-title { color: var(--accent); }
.alert-warn .alert-title { color: var(--yellow); }
.alert-tip .alert-title { color: var(--green); }

/* Memory Section */
.memory-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.mem-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}
.mem-card h3 {
  font-size: 1rem;
  color: var(--text-bright);
  margin-bottom: 12px;
}
.mem-card .mem-stat {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.85rem;
}
.mem-card .mem-stat:last-child { border-bottom: none; }
.mem-card .mem-stat .mem-val {
  color: var(--text-bright);
  font-family: var(--font-mono);
}
.mem-card ul { padding-left: 18px; }
.mem-card li {
  font-size: 0.82rem;
  color: var(--text-dim);
  margin-bottom: 4px;
}

/* Footer */
.footer {
  text-align: center;
  color: var(--text-dim);
  font-size: 0.78rem;
  padding: 24px;
  border-top: 1px solid var(--border);
  margin-top: 32px;
}

/* Responsive */
@media (max-width: 768px) {
  .memory-grid { grid-template-columns: 1fr; }
  .user-grid { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
"""


def build_html(data: dict, skills: dict, memory_stats: dict,
               topics: dict, skill_xref: dict,
               llm_sections: dict = None) -> str:
    """Assemble the full HTML report."""

    summary = data.get('summary', {})
    window = data.get('window', {})
    users = data.get('users', {})
    sessions = data.get('sessions', [])

    llm = llm_sections or {}

    # Escape helper
    def esc(s):
        if s is None: return ''
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Format number
    def fmt(n):
        if n is None: return '0'
        n = int(n)
        if n >= 1000000: return f'{n/1000000:.1f}M'
        if n >= 1000: return f'{n/1000:.1f}K'
        return str(n)

    # Per-user color
    def user_color(user_name):
        return 'duruo' if user_name == 'duruo' else 'raya'

    # Build stat cards
    stat_cards = f"""
    <div class="stat-card highlight">
      <div class="value">{summary.get('total_sessions', 0)}</div>
      <div class="label">会话数</div>
    </div>
    <div class="stat-card">
      <div class="value">{fmt(summary.get('total_messages', 0))}</div>
      <div class="label">消息数</div>
    </div>
    <div class="stat-card">
      <div class="value">{fmt(summary.get('total_tokens', 0))}</div>
      <div class="label">Token 消耗</div>
    </div>
    <div class="stat-card">
      <div class="value">{summary.get('dm_sessions', 0)}/{summary.get('group_sessions', 0)}</div>
      <div class="label">DM / 群聊</div>
    </div>
    <div class="stat-card">
      <div class="value">{summary.get('unique_skills_used', 0)}/{skill_xref.get('total_skills', 0)}</div>
      <div class="label">Skills 使用率</div>
    </div>
    """

    # User cards
    user_cards = ''
    user_names_order = ['duruo', 'Raya']
    for uname in user_names_order:
        if uname not in users:
            continue
        us = users[uname]
        total_sessions = summary.get('total_sessions', 1) or 1
        pct = round(us['sessions'] / total_sessions * 100)
        dm = us.get('dm_sessions', 0)
        grp = us.get('group_sessions', 0)
        user_cards += f"""
        <div class="user-card">
          <h3>{'👤' if uname == 'duruo' else '👩‍💼'} {esc(uname)} <span style="color:var(--text-dim);font-size:0.8rem;">{pct}% 占比</span></h3>
          <div class="user-stats">
            <div class="mini-stat">
              <div class="num">{us['sessions']}</div>
              <div class="lbl">会话 (DM:{dm}/群:{grp})</div>
            </div>
            <div class="mini-stat">
              <div class="num">{fmt(us['messages'])}</div>
              <div class="lbl">消息数</div>
            </div>
            <div class="mini-stat">
              <div class="num">{fmt(us['input_tokens'])}</div>
              <div class="lbl">Input Tokens</div>
            </div>
            <div class="mini-stat">
              <div class="num">{fmt(us['output_tokens'])}</div>
              <div class="lbl">Output Tokens</div>
            </div>
            <div class="mini-stat" style="grid-column:span 2">
              <div class="num">{us['tool_calls']}</div>
              <div class="lbl">Tool Calls</div>
            </div>
          </div>
        </div>"""

    # Comparison bars
    max_val = max(
        max(users.get('duruo', {}).get('sessions', 1), 1),
        max(users.get('Raya', {}).get('sessions', 1), 1)
    )
    comparison_bars = ''
    metrics = [
        ('会话数', 'sessions'),
        ('消息数', 'messages'),
        ('Tokens', 'input_tokens'),
        ('Tool Calls', 'tool_calls'),
    ]
    for label, key in metrics:
        duruo_v = users.get('duruo', {}).get(key, 0)
        raya_v = users.get('Raya', {}).get(key, 0)
        duruo_pct = round(duruo_v / max(duruo_v + raya_v, 1) * 100)
        raya_pct = round(raya_v / max(duruo_v + raya_v, 1) * 100)
        comparison_bars += f"""
        <div class="bar-row">
          <div class="bar-label">{label}</div>
          <div class="bar-track">
            <div class="bar-fill duruo" style="width:{max(duruo_pct, 3)}%">{fmt(duruo_v)}</div>
            <div class="bar-fill raya" style="width:{max(raya_pct, 3)}%">{fmt(raya_v)}</div>
          </div>
        </div>"""

    # Topic table
    topic_rows = ''
    for t in topics.get('topics', [])[:30]:
        cat = t.get('category', '其他')
        cat_class = {
            '运维/基础设施': '运维', '开发/AI工具': '开发', '飞书/消息': '飞书',
            '个人/效率': '个人', '求职/文档': '求职', '硬件/NUC': '硬件',
            '调研/学习': '调研',
        }.get(cat, '其他')
        topic_rows += f"""
        <tr>
          <td><span class="cat-tag cat-{cat_class}">{esc(cat)}</span></td>
          <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{esc(t['title'])}">{esc(t['title'][:40])}</td>
          <td>{esc(t['user'])}</td>
          <td>{t['messages']}</td>
          <td>{fmt(t['tool_calls'])}</td>
        </tr>"""

    # Category summary cards
    cat_cards = ''
    cats = topics.get('categories', {})
    for cat, info in sorted(cats.items(), key=lambda x: -x[1]['count']):
        cat_class = {
            '运维/基础设施': '运维', '开发/AI工具': '开发', '飞书/消息': '飞书',
            '个人/效率': '个人', '求职/文档': '求职', '硬件/NUC': '硬件',
            '调研/学习': '调研',
        }.get(cat, '其他')
        cat_cards += f"""
        <div class="skill-card">
          <span class="cat-tag cat-{cat_class}">{esc(cat)}</span>
          <span class="skill-count" style="float:right">{info['count']}</span>
          <div class="skill-desc" style="margin-top:8px">
            {info['count']} 个会话 · {fmt(info['total_messages'])} 消息 · {fmt(info['total_tokens'])} tokens
          </div>
        </div>"""

    # Skill usage cards
    skill_cards = ''
    for name, info in skill_xref.get('top_used', [])[:12]:
        count = info['count']
        sinfo = info.get('info', {})
        desc = sinfo.get('description', '')[:100]
        skill_cards += f"""
        <div class="skill-card">
          <div class="skill-name">{esc(name)}</div>
          <div class="skill-count">{count}×</div>
          <div class="skill-desc">{esc(desc)}</div>
        </div>"""

    # LLM analysis sections
    core_skills = llm.get('core_skills', '')
    redundant_skills = llm.get('redundant_skills', '')
    new_skill_ideas = llm.get('new_skill_ideas', '')
    memory_suggestions = llm.get('memory_suggestions', '')
    topic_highlights = llm.get('topic_highlights', '')

    llm_section = ''
    if any([core_skills, redundant_skills, new_skill_ideas, memory_suggestions, topic_highlights]):
        llm_section = '<div class="section">'
        llm_section += '<div class="section-title"><span class="icon">🤖</span> LLM 分析洞察</div>'

        if topic_highlights:
            llm_section += f'<div class="alert alert-info"><div class="alert-title">📋 本周主题亮点</div>{topic_highlights}</div>'
        if core_skills:
            llm_section += f'<div class="alert alert-tip"><div class="alert-title">⭐ 核心高频 Skills</div>{core_skills}</div>'
        if redundant_skills:
            llm_section += f'<div class="alert alert-warn"><div class="alert-title">🔄 冗余/可合并 Skills</div>{redundant_skills}</div>'
        if new_skill_ideas:
            llm_section += f'<div class="alert alert-info"><div class="alert-title">💡 建议新增 Skill</div>{new_skill_ideas}</div>'
        if memory_suggestions:
            llm_section += f'<div class="alert alert-tip"><div class="alert-title">🧠 Memory & Profile 优化建议</div>{memory_suggestions}</div>'

        llm_section += '</div>'

    # Memory section
    mem_html = ''
    for ftype, label in [('memory', 'MEMORY.md'), ('user', 'USER.md')]:
        ms = memory_stats.get(ftype, {})
        char_limit = 5000 if ftype == 'memory' else 2500
        usage_pct = round(ms.get('chars', 0) / char_limit * 100) if ms.get('chars') else 0
        bar_color = 'green' if usage_pct < 50 else ('yellow' if usage_pct < 80 else 'red')
        long_entries = ms.get('long_entries', [])
        mixed = ms.get('mixed_lang_entries', [])

        mem_html += f"""
        <div class="mem-card">
          <h3>📄 {label}</h3>
          <div class="mem-stat"><span>行数</span><span class="mem-val">{ms.get('lines', 0)}</span></div>
          <div class="mem-stat"><span>字符数</span><span class="mem-val">{ms.get('chars', 0)}</span></div>
          <div class="mem-stat"><span>条目数</span><span class="mem-val">{ms.get('entries', 0)}</span></div>
          <div class="mem-stat"><span>分区数</span><span class="mem-val">{ms.get('sections', 0)}</span></div>
          <div class="mem-stat"><span>容量</span><span class="mem-val">{fmt(ms.get('chars', 0))}/{fmt(char_limit)}</span></div>
          <div class="bar-row" style="margin-top:8px">
            <div class="bar-label" style="width:50px">使用率</div>
            <div class="bar-track" style="height:14px">
              <div class="bar-fill {bar_color}" style="width:{min(usage_pct,100)}%">{usage_pct}%</div>
            </div>
          </div>"""

        if long_entries:
            mem_html += '<div style="margin-top:10px"><strong style="color:var(--yellow);font-size:0.82rem">⚠️ 长条目:</strong><ul>'
            for le in long_entries[:3]:
                mem_html += f'<li>{esc(le["preview"])}... ({le["length"]} 字符)</li>'
            mem_html += '</ul></div>'

        if mixed:
            mem_html += '<div style="margin-top:10px"><strong style="color:var(--yellow);font-size:0.82rem">🌐 中英混合条目:</strong> '
            mem_html += f'{len(mixed)} 个</div>'

        mem_html += '</div>'

    # Unused skills warning
    unused_alert = ''
    unused_count = len(skill_xref.get('unused', []))
    if unused_count > 20:
        unused_alert = f"""
        <div class="alert alert-warn">
          <div class="alert-title">⚠️ {unused_count} 个 Skills 本周未使用</div>
          共 {skill_xref.get('total_skills', 0)} 个 Skill，使用率仅 {skill_xref.get('usage_rate', 0)}%。大量 Skill 可能冗余或过时。
        </div>"""

    # Put it all together
    wfrom = window.get('from', '')[:10]
    wto = window.get('to', '')[:10]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes 周报 — {wfrom} ~ {wto}</title>
<style>{CSS}</style>
</head>
<body>

<div class="container">

  <!-- Header -->
  <div class="header">
    <h1>📊 Hermes Agent 周报</h1>
    <div class="subtitle">Duruo & Raya · 自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')} CST</div>
    <div class="window-badge">📅 {wfrom} → {wto}</div>
  </div>

  <!-- Section 1: Overview -->
  <div class="section">
    <div class="section-title"><span class="icon">📈</span> 本周概览</div>
    <div class="stats-grid">{stat_cards}</div>
  </div>

  <!-- Section 2: User Analysis -->
  <div class="section">
    <div class="section-title"><span class="icon">👥</span> 用户使用分析</div>
    <div class="user-grid">{user_cards}</div>
    <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:20px">
      <div style="color:var(--text-dim);font-size:0.85rem;margin-bottom:12px">Duruo (蓝) vs Raya (绿) 对比</div>
      {comparison_bars}
    </div>
  </div>

  <!-- Section 3: Topics -->
  <div class="section">
    <div class="section-title"><span class="icon">🏷️</span> 聊天主题 & 进展</div>
    <div class="skill-grid" style="margin-bottom:16px">{cat_cards}</div>
    <div style="overflow-x:auto">
      <table class="topic-table">
        <thead><tr><th>分类</th><th>标题</th><th>用户</th><th>消息</th><th>工具调用</th></tr></thead>
        <tbody>{topic_rows}</tbody>
      </table>
    </div>
    {unused_alert}
  </div>

  <!-- Section 3.5: LLM Insights -->
  {llm_section}

  <!-- Section 4: Skill Report -->
  <div class="section">
    <div class="section-title"><span class="icon">🧩</span> Skill 调用报表</div>
    <div class="stats-grid" style="margin-bottom:16px">
      <div class="stat-card"><div class="value">{skill_xref.get('total_skills', 0)}</div><div class="label">总 Skills</div></div>
      <div class="stat-card"><div class="value">{skill_xref.get('total_used', 0)}</div><div class="label">本周使用</div></div>
      <div class="stat-card"><div class="value">{skill_xref.get('usage_rate', 0)}%</div><div class="label">使用率</div></div>
      <div class="stat-card"><div class="value">{unused_count}</div><div class="label">未使用</div></div>
    </div>
    <div class="skill-grid">{skill_cards}</div>
  </div>

  <!-- Section 5: Memory & Profile -->
  <div class="section">
    <div class="section-title"><span class="icon">🧠</span> Memory & Profile 健康度</div>
    <div class="memory-grid">{mem_html}</div>
  </div>

  <!-- Footer -->
  <div class="footer">
    Generated by Hermes Agent Weekly Review Cron · {datetime.now().strftime('%Y-%m-%d %H:%M')} CST<br>
    data from ~/.hermes/state.db · skills from ~/.hermes/skills/
  </div>

</div>
</body>
</html>"""

    return html


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Generate Weekly Review HTML Report')
    parser.add_argument('--json', required=True, help='Path to weekly_data JSON from Phase 1')
    parser.add_argument('--output', required=True, help='Output HTML path')
    parser.add_argument('--topics', help='Optional LLM-generated topics JSON')
    parser.add_argument('--skill-audit', help='Optional LLM skill audit JSON')
    parser.add_argument('--memory-review', help='Optional LLM memory review JSON')
    args = parser.parse_args()

    # Read Phase 1 data
    with open(args.json) as f:
        data = json.load(f)
    print(f"[report] Loaded {len(data.get('sessions', []))} sessions from {args.json}")

    # Scan skills
    skills = scan_skills()
    print(f"[report] Found {len(skills)} skills in {SKILLS_DIR}")

    # Memory stats
    memory_stats = read_memory_stats()
    print(f"[report] Memory: {memory_stats['memory'].get('entries', 0)} entries ({memory_stats['memory'].get('chars', 0)} chars)")
    print(f"[report] User: {memory_stats['user'].get('entries', 0)} entries ({memory_stats['user'].get('chars', 0)} chars)")

    # Topic analysis
    topics = analyze_topics(data)
    print(f"[report] Topics: {len(topics['topics'])} sessions across {len(topics['categories'])} categories")

    # Skill cross-reference
    skill_xref = cross_reference_skills(data, skills)
    print(f"[report] Skills: {skill_xref['total_used']}/{skill_xref['total_skills']} used ({skill_xref['usage_rate']}%)")

    # Load optional LLM sections
    llm_sections = {}
    if args.topics and os.path.exists(args.topics):
        with open(args.topics) as f:
            llm_sections.update(json.load(f))
    if args.skill_audit and os.path.exists(args.skill_audit):
        with open(args.skill_audit) as f:
            llm_sections.update(json.load(f))
    if args.memory_review and os.path.exists(args.memory_review):
        with open(args.memory_review) as f:
            llm_sections.update(json.load(f))

    # Generate HTML
    html = build_html(data, skills, memory_stats, topics, skill_xref, llm_sections)

    # Write
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"[report] Written: {args.output} ({size_kb:.1f} KB)")
    print(f"[report] Done ✅")


if __name__ == '__main__':
    main()
