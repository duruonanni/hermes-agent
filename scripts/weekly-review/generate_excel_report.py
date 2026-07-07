#!/usr/bin/env python3
"""
Weekly Review Excel Report Generator
Reads Phase 1 JSON + skills + memories → generates 6-sheet .xlsx via OfficeCLI.

Usage:
  python3 generate_excel_report.py \\
    --json data/weekly_data_2026-07-07.json \\
    --output output/report_test.xlsx

  # With optional LLM analysis (Phase 2)
  python3 generate_excel_report.py \\
    --json data/weekly_data_2026-07-07.json \\
    --output output/weekly_report.xlsx \\
    --topics data/llm_analysis.json \\
    --skill-audit data/llm_analysis.json \\
    --memory-review data/llm_analysis.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from typing import Any

# Reuse helpers from HTML report generator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_report import (  # noqa: E402
    analyze_topics,
    cross_reference_skills,
    read_memory_stats,
    scan_skills,
)

SKILLS_DIR = os.path.expanduser('~/.hermes/skills')
HEADER_FILL = '1F4E79'
HEADER_FONT = 'FFFFFF'
ALT_FILL = 'F2F2F2'

STATUS_FILLS = {
    '活跃': 'C6EFCE',
    '冗余': 'FFE699',
    '需增强': 'FFC7CE',
    '建议新增': 'BDD7EE',
    '待审计': 'E7E6E6',
}


def officecli(*args: str) -> str:
    """Run officecli and return stdout."""
    result = subprocess.run(
        ['officecli'] + list(args),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or '')[:200]
        print(f'[WARN] officecli failed: {err}')
    return result.stdout


def batch_ops(file_path: str, ops: list[dict]) -> None:
    """Execute a batch of officecli operations."""
    if not ops:
        return
    payload = json.dumps(ops, ensure_ascii=False)
    result = subprocess.run(
        ['officecli', 'batch', file_path],
        input=payload,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or '')[:200]
        print(f'[WARN] batch failed ({len(ops)} ops): {err}')


def col_letter(col: int) -> str:
    """Convert 1-based column index to Excel letter."""
    letters = ''
    while col > 0:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def cell_path(sheet: str, row: int, col: int) -> str:
    return f'/{sheet}/{col_letter(col)}{row}'


def set_cell(file_path: str, sheet: str, row: int, col: int, value: Any,
             props: dict | None = None) -> dict:
    """Build a batch set op for one cell."""
    p: dict = {}
    if isinstance(value, str):
        p['value'] = value
        # Prevent Excel from interpreting == headings or leading = as formulas
        if value.startswith('=') or value.startswith('+') or value.startswith('-'):
            p['type'] = 'string'
            p['numberformat'] = '@'
    else:
        p['value'] = value
    if props:
        p.update(props)
    return {'command': 'set', 'path': cell_path(sheet, row, col), 'props': p}


def format_header_row(ops: list, sheet: str, row: int, headers: list[str]) -> None:
    for i, h in enumerate(headers, start=1):
        ops.append(set_cell(file_path='', sheet=sheet, row=row, col=i, value=h,
                            props={'bold': True, 'fill': HEADER_FILL, 'font.color': HEADER_FONT}))


def format_data_row(ops: list, sheet: str, row: int, values: list[Any],
                    alt: bool = False) -> None:
    props = {'fill': ALT_FILL} if alt and row % 2 == 0 else None
    for i, v in enumerate(values, start=1):
        cell_props = dict(props) if props else {}
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            cell_props.setdefault('numberformat', '#,##0')
        ops.append(set_cell(file_path='', sheet=sheet, row=row, col=i, value=v,
                            props=cell_props or None))


def format_number(n: int | float) -> str:
    """Human-readable number for overview sheet."""
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n / 1_000:.1f}K'
    return str(n)


def session_progress(session: dict) -> str:
    if session.get('ended_at'):
        return '已完成'
    return '进行中'


def load_llm_sections(args: argparse.Namespace) -> dict:
    """Merge optional LLM analysis JSON files."""
    llm: dict = {}
    for attr in ('topics', 'skill_audit', 'memory_review'):
        path = getattr(args, attr.replace('-', '_'), None)
        if path and os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                llm.update(json.load(f))
    return llm


def build_skill_optimization_rows(
    skills: dict,
    skill_xref: dict,
    llm: dict,
) -> list[list[Any]]:
    """Build Skill优化 sheet rows."""
    rows: list[list[Any]] = []
    audit_items = {}

    # LLM audit may be a list or dict keyed by skill name
    raw_audit = llm.get('skill_audit') or llm.get('skills') or llm.get('audit') or []
    if isinstance(raw_audit, dict):
        audit_items = raw_audit
    elif isinstance(raw_audit, list):
        for item in raw_audit:
            name = item.get('name') or item.get('skill') or ''
            if name:
                audit_items[name] = item

    used = skill_xref.get('used', {})
    unused = set(skill_xref.get('unused', []))

    for name, info in sorted(skills.items()):
        count = used.get(name, {}).get('count', 0) if name in used else 0
        audit = audit_items.get(name, {})

        if audit:
            status = audit.get('status', audit.get('state', ''))
            reason = audit.get('reason', audit.get('rationale', ''))
            priority = audit.get('priority', audit.get('prio', ''))
            action = audit.get('action', audit.get('suggestion', ''))
        elif name in unused:
            status = '待审计'
            reason = '本周未被调用'
            priority = '低'
            action = '评估是否保留或归档'
        elif count >= 5:
            status = '活跃'
            reason = f'本周调用 {count} 次'
            priority = '低'
            action = '保持维护'
        elif count >= 1:
            status = '活跃'
            reason = f'本周调用 {count} 次'
            priority = '中'
            action = '关注使用场景'
        else:
            status = '待审计'
            reason = '无调用记录'
            priority = '低'
            action = '评估是否保留'

        # Only include rows with actionable data — skip pure "待审计" fallbacks
        is_fallback = (status == '待审计') and ('未' in reason or '无' in reason) and action in ('评估是否保留或归档', '评估是否保留')
        if not is_fallback:
            rows.append([name, status, reason, priority, action])

    # Suggested new skills from LLM — new_skill_ideas is an HTML string, NOT a list
    raw_ideas = llm.get('new_skill_ideas', llm.get('suggested_skills', []))
    if isinstance(raw_ideas, str):
        # Extract skill name suggestions from HTML using regex
        import re
        suggestions = re.findall(r'<(?:strong|b)>([^<]+)</(?:strong|b)>', raw_ideas)
        for s in suggestions[:15]:
            s = s.strip()
            if s:
                rows.append([s, '建议新增', 'LLM 分析建议', '中', '创建新 Skill'])
    elif isinstance(raw_ideas, list):
        for idea in raw_ideas:
            if isinstance(idea, str):
                rows.append([idea, '建议新增', 'LLM 分析建议', '中', '创建新 Skill'])
            elif isinstance(idea, dict):
                rows.append([
                    idea.get('name', '新 Skill'),
                    '建议新增',
                    idea.get('reason', 'LLM 分析建议'),
                    idea.get('priority', '中'),
                    idea.get('action', '创建新 Skill'),
                ])

    return rows


def excel_safe_entry_text(value: str) -> str:
    """Prefix formula-like headings so Excel stores them as plain text."""
    if isinstance(value, str) and value.startswith('='):
        return '\u200b' + value
    return value


def force_text_cell_props(value: str) -> dict:
    """Props so Excel stores leading = / + / - as text, not formulas."""
    if isinstance(value, str) and (
        value.startswith('=') or value.startswith('+') or value.startswith('-')
    ):
        return {'type': 'string', 'numberformat': '@'}
    return {}


def build_memory_optimization_rows(memory_stats: dict, llm: dict) -> list[list[Any]]:
    """Build Memory优化 sheet rows."""
    rows: list[list[Any]] = []

    # LLM memory review items
    llm_items = llm.get('memory_items') or llm.get('memory_review') or []
    if isinstance(llm_items, list):
        for item in llm_items:
            if isinstance(item, dict):
                entry = item.get('entry', item.get('preview', ''))
                rows.append([
                    item.get('file', ''),
                    excel_safe_entry_text(entry) if isinstance(entry, str) else entry,
                    item.get('issue_type', item.get('type', '')),
                    item.get('suggestion', item.get('action', '')),
                    item.get('priority', '中'),
                ])

    if rows:
        return rows

    # Heuristic analysis from memory stats
    limits = {'memory': 5000, 'user': 2500}
    labels = {'memory': 'MEMORY.md', 'user': 'USER.md'}

    for key, label in labels.items():
        ms = memory_stats.get(key, {})
        if not ms:
            continue

        chars = ms.get('chars', 0)
        limit = limits[key]
        usage = chars / limit if limit else 0

        if usage > 0.8:
            rows.append([
                label, '(整体)', '待分析',
                f'文件已达 {chars} 字符，接近 {limit} 字符上限',
                '高' if usage > 0.95 else '中',
            ])

        for entry in ms.get('long_entries', []):
            preview = entry.get('preview', '')[:60]
            rows.append([
                label,
                excel_safe_entry_text(preview) if isinstance(preview, str) else preview,
                '待分析',
                f'单条目 {entry.get("length", 0)} 字符，建议拆分',
                '中',
            ])

        for entry in ms.get('mixed_lang_entries', []):
            preview = entry.get('preview', '')[:60]
            rows.append([
                label,
                excel_safe_entry_text(preview) if isinstance(preview, str) else preview,
                '待分析',
                '中英文混杂，建议按语言或主题拆分',
                '低',
            ])

    if not rows:
        rows.append(['MEMORY.md', '-', '-', '暂无问题', '低'])

    return rows


def build_workbook(
    file_path: str,
    data: dict,
    skills: dict,
    memory_stats: dict,
    topics: dict,
    skill_xref: dict,
    llm: dict,
) -> None:
    """Create and populate the 6-sheet workbook."""
    summary = data.get('summary', {})
    window = data.get('window', {})
    users = data.get('users', {})
    skills_mentioned = data.get('skills_mentioned', {})

    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    if os.path.exists(file_path):
        os.remove(file_path)

    officecli('create', file_path)
    officecli('open', file_path)

    sheet_names = ['概览', '主题清单', '使用分析', 'Skill调用', 'Skill优化', 'Memory优化']

    # Rename Sheet1 and add remaining sheets
    officecli('set', file_path, '/Sheet1', '--prop', f'name={sheet_names[0]}')
    for name in sheet_names[1:]:
        officecli('add', file_path, '/', '--type', 'sheet', '--prop', f'name={name}')

    ops: list[dict] = []

    # ── Sheet 1: 概览 ──
    sheet = '概览'
    ops.append(set_cell(file_path, sheet, 1, 1, 'Hermes Agent 周报',
                        {'bold': True, 'font.size': '16pt'}))
    win_from = window.get('from', '')[:10]
    win_to = window.get('to', '')[:10]
    ops.append(set_cell(file_path, sheet, 2, 1, f'时间窗口: {win_from} ~ {win_to}'))

    usage_rate = skill_xref.get('usage_rate', 0)
    metrics = [
        ('会话数', summary.get('total_sessions', 0)),
        ('消息数', format_number(summary.get('total_messages', 0))),
        ('Token消耗', format_number(summary.get('total_tokens', 0))),
        ('DM会话', summary.get('dm_sessions', 0)),
        ('群聊会话', summary.get('group_sessions', 0)),
        ('用户数', summary.get('user_count', 0)),
        ('Skills使用率', f'{usage_rate}%'),
        ('已用 Skills', skill_xref.get('total_used', 0)),
        ('Skills 总量', skill_xref.get('total_skills', 0)),
    ]
    for i, (label, val) in enumerate(metrics, start=4):
        ops.append(set_cell(file_path, sheet, i, 1, label, {'bold': True}))
        ops.append(set_cell(file_path, sheet, i, 2, val))

    ops.append({'command': 'set', 'path': f'/{sheet}/col[A]', 'props': {'width': 22}})
    ops.append({'command': 'set', 'path': f'/{sheet}/col[B]', 'props': {'width': 18}})

    # ── Sheet 2: 主题清单 ──
    sheet = '主题清单'
    headers = ['分类', '标题', '用户', '消息数', '工具调用', '进展状态']
    topic_map = {}
    for t in llm.get('topics', llm.get('session_topics', [])):
        if isinstance(t, dict) and t.get('session_id'):
            topic_map[t['session_id']] = t

    for i, h in enumerate(headers, start=1):
        ops.append(set_cell(file_path, sheet, 1, i, h,
                            {'bold': True, 'fill': HEADER_FILL, 'font.color': HEADER_FONT}))

    row = 2
    for s in data.get('sessions', []):
        llm_topic = topic_map.get(s['id'], {})
        cat = llm_topic.get('category') or next(
            (t['category'] for t in topics.get('topics', []) if t['session_id'] == s['id']),
            '其他',
        )
        status = llm_topic.get('status', llm_topic.get('progress', session_progress(s)))
        values = [
            cat,
            s.get('title', '')[:80],
            s.get('user', ''),
            s.get('message_count', 0),
            s.get('tool_calls', 0),
            status,
        ]
        alt = row % 2 == 0
        for i, v in enumerate(values, start=1):
            props = {'fill': ALT_FILL} if alt else {}
            if isinstance(v, int):
                props['numberformat'] = '#,##0'
            ops.append(set_cell(file_path, sheet, row, i, v, props or None))
        row += 1

    ops.append({'command': 'set', 'path': f'/{sheet}', 'props': {'freeze': 'A2'}})
    widths = [18, 35, 12, 10, 10, 12]
    for i, w in enumerate(widths, start=1):
        ops.append({'command': 'set', 'path': f'/{sheet}/col[{col_letter(i)}]', 'props': {'width': w}})

    # ── Sheet 3: 使用分析 ──
    sheet = '使用分析'
    headers = ['用户', '会话数', '消息数', 'Input Tokens', 'Output Tokens',
               '工具调用', 'DM会话', '群聊会话']
    for i, h in enumerate(headers, start=1):
        ops.append(set_cell(file_path, sheet, 1, i, h,
                            {'bold': True, 'fill': HEADER_FILL, 'font.color': HEADER_FONT}))

    totals = defaultdict(int)
    row = 2
    for uname, stats in sorted(users.items()):
        values = [
            uname,
            stats.get('sessions', 0),
            stats.get('messages', 0),
            stats.get('input_tokens', 0),
            stats.get('output_tokens', 0),
            stats.get('tool_calls', 0),
            stats.get('dm_sessions', 0),
            stats.get('group_sessions', 0),
        ]
        for k, v in zip(
            ['sessions', 'messages', 'input_tokens', 'output_tokens',
             'tool_calls', 'dm_sessions', 'group_sessions'],
            values[1:],
        ):
            totals[k] += v
        alt = row % 2 == 0
        for i, v in enumerate(values, start=1):
            props = {'fill': ALT_FILL} if alt else {}
            if isinstance(v, int):
                props['numberformat'] = '#,##0'
            ops.append(set_cell(file_path, sheet, row, i, v, props or None))
        row += 1

    # Total row
    total_vals = [
        '合计',
        totals['sessions'], totals['messages'],
        totals['input_tokens'], totals['output_tokens'],
        totals['tool_calls'], totals['dm_sessions'], totals['group_sessions'],
    ]
    for i, v in enumerate(total_vals, start=1):
        props = {'bold': True}
        if isinstance(v, int):
            props['numberformat'] = '#,##0'
        ops.append(set_cell(file_path, sheet, row, i, v, props))

    ops.append({'command': 'set', 'path': f'/{sheet}', 'props': {'freeze': 'A2'}})
    for i, w in enumerate([14, 10, 10, 14, 14, 10, 10, 10], start=1):
        ops.append({'command': 'set', 'path': f'/{sheet}/col[{col_letter(i)}]', 'props': {'width': w}})

    # ── Sheet 4: Skill调用 ──
    sheet = 'Skill调用'
    headers = ['Skill名', '分类', '版本', '本周调用', '描述']
    for i, h in enumerate(headers, start=1):
        ops.append(set_cell(file_path, sheet, 1, i, h,
                            {'bold': True, 'fill': HEADER_FILL, 'font.color': HEADER_FONT}))

    skill_rows = []
    for name, info in sorted(skills.items()):
        count = skills_mentioned.get(name, 0)
        skill_rows.append([
            name,
            info.get('category', ''),
            info.get('version', '') or '-',
            count,
            info.get('description', '')[:100],
        ])
    # Skills used but not in inventory
    for name, count in skills_mentioned.items():
        if name not in skills:
            skill_rows.append([name, '(未入库)', '-', count, ''])

    skill_rows.sort(key=lambda r: (-r[3], r[0]))
    for r_idx, values in enumerate(skill_rows, start=2):
        alt = r_idx % 2 == 0
        for i, v in enumerate(values, start=1):
            props = {'fill': ALT_FILL} if alt else {}
            if isinstance(v, int):
                props['numberformat'] = '#,##0'
            ops.append(set_cell(file_path, sheet, r_idx, i, v, props or None))

    ops.append({'command': 'set', 'path': f'/{sheet}', 'props': {'freeze': 'A2'}})
    for i, w in enumerate([28, 18, 10, 10, 45], start=1):
        ops.append({'command': 'set', 'path': f'/{sheet}/col[{col_letter(i)}]', 'props': {'width': w}})

    # ── Sheet 5: Skill优化 ──
    sheet = 'Skill优化'
    headers = ['Skill名', '状态', '理由', '优先级', '建议动作']
    for i, h in enumerate(headers, start=1):
        ops.append(set_cell(file_path, sheet, 1, i, h,
                            {'bold': True, 'fill': HEADER_FILL, 'font.color': HEADER_FONT}))

    opt_rows = build_skill_optimization_rows(skills, skill_xref, llm)
    for r_idx, values in enumerate(opt_rows, start=2):
        alt = r_idx % 2 == 0
        status = values[1] if len(values) > 1 else ''
        for i, v in enumerate(values, start=1):
            props: dict = {}
            if alt:
                props['fill'] = ALT_FILL
            if i == 2 and status in STATUS_FILLS:
                props['fill'] = STATUS_FILLS[status]
            ops.append(set_cell(file_path, sheet, r_idx, i, v, props or None))

    ops.append({'command': 'set', 'path': f'/{sheet}', 'props': {'freeze': 'A2'}})
    for i, w in enumerate([28, 12, 35, 10, 30], start=1):
        ops.append({'command': 'set', 'path': f'/{sheet}/col[{col_letter(i)}]', 'props': {'width': w}})

    # ── Sheet 6: Memory优化 ──
    sheet = 'Memory优化'
    headers = ['文件', '条目', '问题类型', '建议', '优先级']
    for i, h in enumerate(headers, start=1):
        ops.append(set_cell(file_path, sheet, 1, i, h,
                            {'bold': True, 'fill': HEADER_FILL, 'font.color': HEADER_FONT}))

    mem_rows = build_memory_optimization_rows(memory_stats, llm)
    for r_idx, values in enumerate(mem_rows, start=2):
        alt = r_idx % 2 == 0
        for i, v in enumerate(values, start=1):
            props = {'fill': ALT_FILL} if alt else {}
            if i == 2 and isinstance(v, str):
                props.update(force_text_cell_props(v))
            ops.append(set_cell(file_path, sheet, r_idx, i, v, props or None))

    ops.append({'command': 'set', 'path': f'/{sheet}', 'props': {'freeze': 'A2'}})
    for i, w in enumerate([16, 30, 12, 40, 10], start=1):
        ops.append({'command': 'set', 'path': f'/{sheet}/col[{col_letter(i)}]', 'props': {'width': w}})

    # Execute in chunks
    chunk_size = 60
    for i in range(0, len(ops), chunk_size):
        batch_ops(file_path, ops[i:i + chunk_size])

    # Conditional formatting for Skill优化 status column
    for status, fill in STATUS_FILLS.items():
        officecli(
            'add', file_path, f'/{sheet_names[4]}',
            '--type', 'conditionalformatting',
            '--prop', 'type=containsText',
            '--prop', 'ref=B2:B500',
            '--prop', f'text={status}',
            '--prop', f'fill={fill}',
        )

    # Tab colors
    tab_colors = ['1F4E79', '2E75B6', '548235', 'BF8F00', 'C55A11', '7030A0']
    for name, color in zip(sheet_names, tab_colors):
        officecli('set', file_path, f'/{name}', '--prop', f'tabColor={color}')

    officecli('save', file_path)
    officecli('close', file_path)


def main():
    parser = argparse.ArgumentParser(description='Generate weekly Excel report')
    parser.add_argument('--json', required=True, help='Phase 1 weekly data JSON')
    parser.add_argument('--output', required=True, help='Output .xlsx path')
    parser.add_argument('--topics', help='Optional LLM topics JSON')
    parser.add_argument('--skill-audit', dest='skill_audit', help='Optional LLM skill audit JSON')
    parser.add_argument('--memory-review', dest='memory_review', help='Optional LLM memory review JSON')
    args = parser.parse_args()

    with open(args.json, encoding='utf-8') as f:
        data = json.load(f)

    skills = scan_skills()
    memory_stats = read_memory_stats()
    topics = analyze_topics(data)
    skill_xref = cross_reference_skills(data, skills)
    llm = load_llm_sections(args)

    print(f'[excel] Sessions: {data["summary"]["total_sessions"]}')
    print(f'[excel] Skills inventory: {len(skills)}')
    print(f'[excel] Skills used: {skill_xref["total_used"]}')
    print(f'[excel] Topics: {len(topics["topics"])}')

    build_workbook(args.output, data, skills, memory_stats, topics, skill_xref, llm)

    print(f'[excel] Output: {args.output}')

    # Validate
    result = subprocess.run(
        ['officecli', 'validate', args.output],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print('[excel] Validation: passed')
    else:
        print(f'[excel] Validation: {result.stderr[:200]}')


if __name__ == '__main__':
    main()
