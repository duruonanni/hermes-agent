#!/usr/bin/env python3
"""
Weekly Data Collection Script (Phase 1)
no_agent=True script — zero token cost
Extracts session data from Hermes state.db for the report window

Usage:
  python3 ~/hermes-workspace/projects/weekly-review/scripts/collect_weekly_data.py
  python3 ~/hermes-workspace/projects/weekly-review/scripts/collect_weekly_data.py --date 2026-07-02
"""

import sqlite3
import json
import os
import re
import sys
import argparse
from datetime import datetime, date, timedelta, time as dt_time
from typing import Any

DB_PATH = os.path.expanduser('~/.hermes/state.db')
PROJECT_DIR = os.path.expanduser('~/hermes-workspace/projects/weekly-review')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'data')

USERS = {
    'ou_33ac860a73d2c8c18203ca55a237881a': 'duruo',
    'ou_699fbd27d38d19606c83ece40ee21b7d': 'Raya',
}

# Skills loaded via skill_view() during sessions
# Multi-pattern detection: tool results, assistant calls, system invokes, cron associations


def get_report_window(reference_date: date = None) -> tuple[datetime, datetime]:
    """Get last Thursday to this Thursday window."""
    if reference_date is None:
        reference_date = date.today()

    # Thursday = weekday 3 (Mon=0, Tue=1, Wed=2, Thu=3)
    # Find the last Thursday (including today if today is Thursday)
    days_since_thu = (reference_date.weekday() - 3) % 7
    last_thu = reference_date - timedelta(days=days_since_thu)
    next_thu = last_thu + timedelta(days=7)

    from_dt = datetime.combine(last_thu, dt_time.min)
    to_dt = datetime.combine(next_thu, dt_time.min)

    return from_dt, to_dt


def query_data(from_ts: float, to_ts: float) -> dict[str, Any]:
    """Extract all session data in the time window."""
    if not os.path.exists(DB_PATH):
        return {'error': f'Database not found: {DB_PATH}'}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    result = {
        'window': {
            'from': datetime.fromtimestamp(from_ts).isoformat(),
            'to': datetime.fromtimestamp(to_ts).isoformat(),
        },
        'sessions': [],
        'users': {},
        'skills_mentioned': {},
        'summary': {},
    }

    # Sessions in window (feishu only, excluding cron/subagent)
    c.execute("""
        SELECT s.id, s.source, s.user_id, s.title, s.started_at, s.ended_at,
               s.message_count, s.chat_type, s.chat_id, s.thread_id,
               s.input_tokens, s.output_tokens, s.tool_call_count,
               s.model
        FROM sessions s
        WHERE s.started_at >= ? AND s.started_at < ?
          AND s.source = 'feishu'
        ORDER BY s.started_at ASC
    """, (from_ts, to_ts))

    sessions_raw = c.fetchall()
    session_ids = []
    user_stats = {}
    skill_mentions = {}

    for row in sessions_raw:
        s = dict(row)
        uid = s['user_id'] or ''
        uname = USERS.get(uid, uid)
        s['user_name'] = uname
        chat_type = s['chat_type'] or 'dm'

        session_ids.append(s['id'])
        result['sessions'].append({
            'id': s['id'],
            'user': uname,
            'user_id': uid,
            'title': s['title'] or '',
            'started_at': s['started_at'],
            'ended_at': s['ended_at'],
            'message_count': s['message_count'],
            'chat_type': chat_type,
            'chat_id': s['chat_id'],
            'input_tokens': s['input_tokens'] or 0,
            'output_tokens': s['output_tokens'] or 0,
            'tool_calls': s['tool_call_count'] or 0,
            'model': s['model'] or '',
        })

        # Per-user stats
        if uname not in user_stats:
            user_stats[uname] = {
                'sessions': 0, 'messages': 0, 'input_tokens': 0,
                'output_tokens': 0, 'tool_calls': 0, 'dm_sessions': 0,
                'group_sessions': 0, 'titles': []
            }
        stats = user_stats[uname]
        stats['sessions'] += 1
        stats['messages'] += s['message_count'] or 0
        stats['input_tokens'] += s['input_tokens'] or 0
        stats['output_tokens'] += s['output_tokens'] or 0
        stats['tool_calls'] += s['tool_call_count'] or 0
        if chat_type == 'dm':
            stats['dm_sessions'] += 1
        elif chat_type == 'group':
            stats['group_sessions'] += 1
        if s['title'] and s['title'] != 'untitled':
            stats['titles'].append(s['title'])

    # Now get messages for these sessions (limit to user + assistant for topic extraction)
    if session_ids:
        placeholders = ','.join(['?'] * len(session_ids))

        # Get user messages (last 3 per session for topic context)
        c.execute(f"""
            SELECT m.session_id, m.role, m.content, m.timestamp
            FROM messages m
            WHERE m.session_id IN ({placeholders})
              AND m.role IN ('user', 'assistant')
              AND m.content IS NOT NULL AND m.content != ''
            ORDER BY m.timestamp ASC
        """, session_ids)

        all_messages = [dict(m) for m in c.fetchall()]

        # ═══ Multi-pattern skill detection ═══
        # Known tool/function names to exclude (not real skills)
        TOOL_NAMES = {
            'terminal', 'web_search', 'read_file', 'session_search', 'cronjob',
            'search_files', 'process', 'skill_view', 'todo', 'browser_navigate',
            'web_extract', 'write_file', 'skill_manage', 'execute_code',
            'delegate_task', 'memory', 'browser_vision', 'browser_console',
            'feishu_doc_read', 'patch', 'vision_analyze', 'image_generate',
            'text_to_speech', 'browser_click', 'browser_type', 'browser_snapshot',
            'browser_press', 'browser_scroll', 'browser_get_images', 'browser_back',
            'clarify', 'feishu_drive_add_comment', 'feishu_drive_list_comments',
            'feishu_drive_list_comment_replies', 'feishu_drive_reply_comment',
            'mcp_officecli_officecli', 'cron', 'task',
        }

        # Pattern 1: skill_view() TOOL results — JSON with "name" + "description"
        # (filters out cronjob results which have "schedule" instead of "description")
        c.execute(f"""
            SELECT content FROM messages
            WHERE session_id IN ({placeholders})
              AND role = 'tool'
              AND content LIKE '%"name":%'
              AND content LIKE '%"description":%'
        """, session_ids)
        for (content,) in c.fetchall():
            for m in re.finditer(r'"name"\s*:\s*"([^"]+)"', content):
                skill_name = m.group(1)
                # Validate skill-name pattern (lowercase with hyphens/underscores)
                if re.match(r'^[a-z][a-z0-9_-]+(\.[a-z][a-z0-9_-]+)*$', skill_name):
                    if skill_name not in TOOL_NAMES:
                        skill_mentions[skill_name] = skill_mentions.get(skill_name, 0) + 1

        # Pattern 2: cronjob() TOOL results — extract from "skill" and "skills" fields
        c.execute(f"""
            SELECT content FROM messages
            WHERE session_id IN ({placeholders})
              AND role = 'tool'
              AND content LIKE '%"schedule":%'
              AND content LIKE '%"skill"%'
        """, session_ids)
        for (content,) in c.fetchall():
            # Extract single "skill" field: "skill": "skill-name"
            for m in re.finditer(r'"skill"\s*:\s*"([^"]+)"', content):
                sn = m.group(1)
                if sn and sn != 'null' and re.match(r'^[a-z][a-z0-9_-]+(\.[a-z][a-z0-9_-]+)*$', sn):
                    if sn not in TOOL_NAMES:
                        skill_mentions[sn] = skill_mentions.get(sn, 0) + 1
            # Extract list "skills" field: "skills": ["name1", "name2"]
            for m in re.finditer(r'"skills"\s*:\s*\[([^\]]*)\]', content):
                for sn_match in re.finditer(r'"([^"]+)"', m.group(1)):
                    sn = sn_match.group(1)
                    if sn and sn != 'null' and re.match(r'^[a-z][a-z0-9_-]+(\.[a-z][a-z0-9_-]+)*$', sn):
                        if sn not in TOOL_NAMES:
                            skill_mentions[sn] = skill_mentions.get(sn, 0) + 1

        # Pattern 3: skill_view('name') in assistant messages (inline calls)
        for msg in all_messages:
            if msg['role'] == 'assistant':
                content = msg['content'] or ''
                for m in re.finditer(r"skill_view\s*\(\s*'([^']+)'\s*\)", content):
                    sn = m.group(1)
                    if sn not in TOOL_NAMES:
                        skill_mentions[sn] = skill_mentions.get(sn, 0) + 1

        # Pattern 4: User messages with "[IMPORTANT: ... invoked ... skill]"
        # and system-preloaded skill_view('name') calls in user messages
        for msg in all_messages:
            if msg['role'] == 'user':
                content = msg['content'] or ''
                # System invoke: 'invoked the "xxx" skill'
                for m in re.finditer(r'invoked\s+the\s+"([^"]+)"\s+skill', content):
                    sn = m.group(1)
                    if sn not in TOOL_NAMES:
                        skill_mentions[sn] = skill_mentions.get(sn, 0) + 1
                # skill_view('name') in user messages (system pre-load)
                for m in re.finditer(r"skill_view\s*\(\s*'([^']+)'\s*\)", content):
                    sn = m.group(1)
                    if sn not in TOOL_NAMES:
                        skill_mentions[sn] = skill_mentions.get(sn, 0) + 1

        # Group messages by session for topic extraction (user messages only)
        session_user_msgs = {}
        for msg in all_messages:
            if msg['role'] == 'user':
                sid = msg['session_id']
                if sid not in session_user_msgs:
                    session_user_msgs[sid] = []
                session_user_msgs[sid].append(msg['content'][:300])

        # Attach user message previews to sessions
        for s in result['sessions']:
            s['user_messages'] = session_user_msgs.get(s['id'], [])[:5]

    result['users'] = user_stats
    result['skills_mentioned'] = dict(sorted(
        skill_mentions.items(), key=lambda x: -x[1]
    ))

    # Summary
    result['summary'] = {
        'total_sessions': len(result['sessions']),
        'total_messages': sum(s['message_count'] for s in result['sessions']),
        'total_tokens': sum(
            s['input_tokens'] + s['output_tokens'] for s in result['sessions']
        ),
        'dm_sessions': sum(1 for s in result['sessions'] if s['chat_type'] == 'dm'),
        'group_sessions': sum(1 for s in result['sessions'] if s['chat_type'] == 'group'),
        'user_count': len(user_stats),
        'unique_skills_used': len(skill_mentions),
    }

    conn.close()
    return result


def save_data(data: dict[str, Any], output_path: str = None):
    """Save collected data as JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        today_str = date.today().isoformat()
        output_path = os.path.join(OUTPUT_DIR, f'weekly_data_{today_str}.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Collect weekly Hermes session data')
    parser.add_argument('--date', type=str, help='Reference date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--output', type=str, help='Output path')
    parser.add_argument('--summary-only', action='store_true', help='Only print summary to stdout')
    args = parser.parse_args()

    ref_date = date.fromisoformat(args.date) if args.date else date.today()
    from_dt, to_dt = get_report_window(ref_date)
    from_ts = from_dt.timestamp()
    to_ts = to_dt.timestamp()

    data = query_data(from_ts, to_ts)
    out_path = save_data(data, args.output)

    # Cron output (stdout) — just summary when --summary-only or when run by cron
    summary = data['summary']
    window = data['window']
    print(f"[weekly-data] Window: {window['from'][:10]} ~ {window['to'][:10]}")
    print(f"[weekly-data] Sessions: {summary['total_sessions']}")
    print(f"[weekly-data] Messages: {summary['total_messages']}")
    print(f"[weekly-data] Tokens: {summary['total_tokens']}")
    print(f"[weekly-data] DM/Group: {summary['dm_sessions']}/{summary['group_sessions']}")
    print(f"[weekly-data] Users: {summary['user_count']}")
    print(f"[weekly-data] Skills used: {summary['unique_skills_used']}")
    print(f"[weekly-data] Output: {out_path}")

    if args.summary_only:
        return

    # Print detailed user stats
    for uname, stats in data['users'].items():
        print(f"\n--- {uname} ---")
        print(f"  Sessions: {stats['sessions']} (DM: {stats['dm_sessions']}, Group: {stats['group_sessions']})")
        print(f"  Messages: {stats['messages']}")
        print(f"  Input tokens: {stats['input_tokens']}")
        print(f"  Output tokens: {stats['output_tokens']}")
        print(f"  Tool calls: {stats['tool_calls']}")
        if stats['titles']:
            # Show top 5 titles
            for t in stats['titles'][:5]:
                print(f"    - {t[:60]}")

    # Skill mentions
    if data['skills_mentioned']:
        print("\n--- Skill References ---")
        for skill_name, count in list(data['skills_mentioned'].items())[:20]:
            print(f"  {skill_name}: {count}x")


if __name__ == '__main__':
    main()
