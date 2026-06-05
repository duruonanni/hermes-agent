#!/usr/bin/env python3
"""
skill-lint: Validate SKILL.md frontmatter across all skills.

Checks:
1. Name vs directory basename match
2. Description length (<= 1024 chars)
3. metadata.hermes presence (tags, related_skills, trigger)
4. trigger field valid
5. related_skills entries resolve to real skill dirs (auto-fix eligible)
6. Body-level backtick references -> WARNING only

Outputs JSON to stdout. Exit codes: 0=clean, 1=issues, 2=auto-fixes applied.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

SKILLS_ROOT = os.path.expanduser("~/.hermes/skills")
TRIGGER_VALUES = {"manual", "cron", "slash", "preload"}
MAX_DESCRIPTION_LENGTH = 1024


def _parse_yaml_value(text):
    """Parse a YAML mapping/list/scalar from text lines iteratively."""
    result = {}
    lines = text.split("\n")
    stack = [(result, None, -1)]

    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # List item
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if (item.startswith('"') and item.endswith('"')) or \
               (item.startswith("'") and item.endswith("'")):
                item = item[1:-1]
            while stack and stack[-1][2] >= indent:
                stack.pop()
            if stack:
                parent, pkey, _ = stack[-1]
                if pkey is not None and isinstance(parent, dict):
                    if pkey in parent:
                        val = parent[pkey]
                        if isinstance(val, list):
                            val.append(item)
                        else:
                            parent[pkey] = [val, item]
                    else:
                        parent[pkey] = [item]
            continue

        # Key: value or Key: (empty/map)
        if ": " in stripped or stripped.endswith(":"):
            colon_pos = stripped.find(": ")
            if colon_pos == -1:
                colon_pos = len(stripped) - 1

            key = stripped[:colon_pos].strip()
            val = stripped[colon_pos + 2:].strip() if colon_pos < len(stripped) - 1 else ""

            if (key.startswith('"') and key.endswith('"')) or \
               (key.startswith("'") and key.endswith("'")):
                key = key[1:-1]

            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            elif val == ">":
                val = ""

            while stack and stack[-1][2] >= indent:
                stack.pop()

            if not stack:
                parent = result
            else:
                parent, _, _ = stack[-1]

            if val == "":
                nested = {}
                parent[key] = nested
                stack.append((nested, key, indent))
            else:
                parent[key] = val

    return result


def parse_frontmatter(path):
    """Parse YAML frontmatter. Returns (fm_dict, body_text, error_str)."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None, content, "SKILL.md does not start with '---'"

    rest = content[3:]
    m = re.search(r"\n---\s*\n", rest)
    if not m:
        return None, content, "No closing '---' found for frontmatter"

    fm_text = rest[: m.start()]
    body = rest[m.end():]

    try:
        fm = _parse_yaml_value(fm_text)
    except Exception as e:
        return {}, body, f"YAML parse error: {e}"

    return fm, body, None


def find_all_skills(root):
    """Return list of (skill_dir, skill_path) tuples sorted by name."""
    results = []
    for skill_path in Path(root).rglob("SKILL.md"):
        if ".pre-lint" in str(skill_path):
            continue
        results.append((skill_path.parent, skill_path))
    return sorted(results, key=lambda x: x[0].name)


def build_skill_name_index(root):
    """Build set of valid skill YAML names from all SKILL.md files."""
    names = set()
    for _, path in find_all_skills(root):
        fm, _, err = parse_frontmatter(path)
        if fm and not err and "name" in fm:
            names.add(fm["name"])
    return names


def deep_get(d, *keys, default=None):
    """Safely traverse nested dicts."""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
    return d


def find_related_skills(fm):
    """Extract related_skills list from frontmatter."""
    rs = deep_get(fm, "metadata", "hermes", "related_skills", default=[])
    if not isinstance(rs, list):
        rs = fm.get("related_skills", [])
    if not isinstance(rs, list):
        if isinstance(rs, str):
            rs = [rs]
        else:
            rs = []
    return rs


def find_body_dead_refs(body, valid_names):
    """Find backtick-wrapped strings in body that look like skill names but don't exist."""
    refs = re.findall(r"`([a-z][a-z0-9-]*[a-z0-9])`", body)
    SKIP = {
        "sh", "md", "yml", "yaml", "json", "toml", "env", "git",
        "py", "js", "ts", "go", "rs", "rb", "php", "html", "css",
        "txt", "csv", "xml", "png", "jpg", "gif", "svg", "pdf",
        "http", "https", "api", "url", "uri", "cli", "ui", "ux",
        "stdout", "stdin", "stderr", "config", "debug", "release",
        "curl", "wget", "grep", "sed", "awk", "cat", "less", "tail",
        "head", "find", "ls", "cp", "mv", "rm", "mkdir", "chmod",
        "chown", "ps", "top", "kill", "ssh", "scp", "rsync",
        "git", "hg", "svn", "docker", "kubectl", "helm",
        "pip", "npm", "yarn", "apt", "yum", "brew", "cargo",
        "python3", "node", "ruby", "perl", "php", "go",
        "ffmpeg", "ffprobe", "sox", "convert", "magick",
        "jq", "yq", "xmllint", "csvtool", "pandoc",
        "left", "right", "top", "bottom", "up", "down",
        "name", "type", "kind", "size", "path", "mode",
        "start", "end", "next", "prev", "last", "first",
        "true", "false", "yes", "no", "on", "off",
        "age", "name", "message", "user", "bot",
    }
    dead = []
    for ref in refs:
        if ref in SKIP:
            continue
        if ref not in valid_names:
            dead.append(ref)
    return dead


def check_skill(skill_path, valid_names):
    """Run all checks on a single SKILL.md. Returns result dict."""
    dir_name = skill_path.parent.name
    result = {
        "skill": dir_name,
        "path": str(skill_path),
        "name_dir_match": None,
        "description_length": None,
        "description_ok": None,
        "has_metadata_hermes": None,
        "has_tags": None,
        "trigger_valid": None,
        "trigger_value": None,
        "related_skills_valid": None,
        "body_dead_refs": [],
        "auto_fixed": False,
        "errors": [],
        "warnings": [],
    }

    fm, body, parse_err = parse_frontmatter(skill_path)
    if parse_err:
        result["errors"].append(parse_err)
        return result
    if fm is None:
        result["errors"].append("Could not parse frontmatter")
        return result

    # 1. Name-Dir Match
    yaml_name = fm.get("name", "")
    result["name_dir_match"] = yaml_name == dir_name
    if not result["name_dir_match"]:
        result["warnings"].append(
            f"name '{yaml_name}' != directory '{dir_name}'"
        )

    # 2. Description Length
    desc = fm.get("description", "")
    result["description_length"] = len(desc)
    result["description_ok"] = len(desc) <= MAX_DESCRIPTION_LENGTH
    if not result["description_ok"]:
        result["errors"].append(
            f"description {len(desc)} chars exceeds {MAX_DESCRIPTION_LENGTH} limit"
        )

    # 3. metadata.hermes Presence
    hermes = deep_get(fm, "metadata", "hermes", default={})
    if not isinstance(hermes, dict):
        hermes = {}
    result["has_metadata_hermes"] = len(hermes) > 0
    result["has_tags"] = "tags" in hermes and bool(hermes["tags"])
    if not result["has_metadata_hermes"]:
        result["warnings"].append("Missing metadata.hermes section")

    # 4. Trigger Validation
    trigger = hermes.get("trigger", "") if isinstance(hermes, dict) else ""
    result["trigger_value"] = trigger
    result["trigger_valid"] = trigger in TRIGGER_VALUES
    if not trigger:
        result["warnings"].append("Missing metadata.hermes.trigger")
    elif not result["trigger_valid"]:
        result["warnings"].append(
            f"Invalid trigger value: '{trigger}' (expected: {', '.join(sorted(TRIGGER_VALUES))})"
        )

    # 5. related_skills Validation
    rs_list = find_related_skills(fm)
    broken = [r for r in rs_list if r not in valid_names]
    result["related_skills_valid"] = len(broken) == 0
    if broken:
        result["warnings"].append(
            f"Broken related_skills references: {broken}"
        )

    # 6. Body-Level Dead Refs
    dead_body = find_body_dead_refs(body, valid_names)
    result["body_dead_refs"] = dead_body
    if dead_body:
        seen = set()
        for ref in dead_body:
            if ref in seen:
                continue
            seen.add(ref)
            for i, line in enumerate(body.split("\n"), 1):
                if f"`{ref}`" in line:
                    result["warnings"].append(
                        f"Body text references `{ref}` at line ~{i} (WARNING only)"
                    )
                    break

    return result


def auto_fix_related_skills(skill_path, broken_refs):
    """Remove broken related_skills entries from SKILL.md frontmatter."""
    content = skill_path.read_text(encoding="utf-8")
    backup_path = skill_path.with_name(".pre-lint.SKILL.md")

    if not backup_path.exists():
        shutil.copy2(str(skill_path), str(backup_path))

    orig_content = content
    for ref in broken_refs:
        patterns = [
            f"- {ref}",
            f"- '{ref}'",
            f'- "{ref}"',
        ]
        for pat in patterns:
            lines = content.split("\n")
            new_lines = [l for l in lines if l.strip() != pat]
            content = "\n".join(new_lines)

    if content != orig_content:
        skill_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    root = os.path.expanduser(SKILLS_ROOT)
    if not os.path.isdir(root):
        print(json.dumps({
            "timestamp": "",
            "summary": {"total_skills": 0, "errors": 0, "warnings": 0, "auto_fixed": 0},
            "results": [],
            "auto_fixes": [],
            "error": f"Skills directory not found: {root}"
        }))
        return 1

    from datetime import datetime
    now = datetime.now().isoformat()

    valid_names = build_skill_name_index(root)

    results = []
    auto_fixes = []
    total_errors = 0
    total_warnings = 0
    total_fixed = 0

    for skill_dir, skill_path in find_all_skills(root):
        result = check_skill(skill_path, valid_names)
        errors = result["errors"]
        warnings = result["warnings"]

        # Auto-fix broken related_skills in frontmatter
        if not result["related_skills_valid"]:
            fm, _, _ = parse_frontmatter(skill_path)
            if fm:
                rs_list = find_related_skills(fm)
                broken = [r for r in rs_list if r not in valid_names]
                if broken and auto_fix_related_skills(skill_path, broken):
                    result["auto_fixed"] = True
                    total_fixed += 1
                    auto_fixes.append({
                        "skill": result["skill"],
                        "file": str(skill_path),
                        "backup": str(skill_path.with_name(".pre-lint.SKILL.md")),
                        "fix": f"Removed broken related_skills entries: {broken}",
                    })
                    # Re-check after fix
                    result = check_skill(skill_path, valid_names)
                    errors = result["errors"]
                    warnings = result["warnings"]

        total_errors += len(errors)
        total_warnings += len(warnings)
        results.append(result)

    output = {
        "timestamp": now,
        "summary": {
            "total_skills": len(results),
            "errors": total_errors,
            "warnings": total_warnings,
            "auto_fixed": total_fixed,
        },
        "results": results,
        "auto_fixes": auto_fixes,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

    if total_fixed > 0:
        return 2
    if total_errors > 0 or total_warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
