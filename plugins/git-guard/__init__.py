"""
git-guard plugin — Intercept destructive git operations via pre_tool_call hook.

Wires one behaviour:

* ``pre_tool_call`` hook — inspects the ``terminal`` tool's ``command`` arg
  for patterns like ``git push --delete``, ``git push --force``, ``git push
  -f``, ``git branch -D``. When a match is found, the tool call is blocked
  and the model is told to use the pre-push hook's env-var bypass
  (GIT_ALLOW_DELETE=1 / GIT_FORCE_PUSH=1) if the action is intentional.

Designed as a layer-2 guard on top of the pre-push git hook (layer 1).
Layer 1 catches pushes before they reach the remote. Layer 2 catches the
model trying to push without going through git (e.g., GitHub API calls).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns: (tool_name, regex_on_command, bypass_env_var, label)
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS: list[tuple[str, str, str]] = [
    # git push --delete <remote> <branch>
    (r"git\s+push\s+.*--delete", "GIT_ALLOW_DELETE", "remote branch deletion"),
    # git push --force / -f
    (r"git\s+push\s+.*--force", "GIT_FORCE_PUSH", "force push"),
    (r"git\s+push\s+.*\s-f\b", "GIT_FORCE_PUSH", "force push"),
    # git branch -D (force delete local)
    (r"git\s+branch\s+-D", "GIT_ALLOW_DELETE", "local branch force deletion"),
    # git push origin :branch (delete remote ref via refspec)
    (r"git\s+push\s+\S+\s+:", "GIT_ALLOW_DELETE", "remote branch deletion (refspec)"),
    # GitHub API: POST/PATCH/DELETE to repos/duruonanni/hermes-agent/*
    (r"github\.com/repos/duruonanni/hermes-agent/(pulls|git)", "GIT_ALLOW_PR", "GitHub API PR/branch write"),
]

# ---------------------------------------------------------------------------
# Hook callback
# ---------------------------------------------------------------------------


def _check_command(tool_name: str, command: str) -> Optional[str]:
    """Return a user-facing block message if *command* matches any
    dangerous pattern, or ``None`` to allow the call."""
    for regex, env_var, label in _DANGEROUS_PATTERNS:
        if re.search(regex, command, re.IGNORECASE):
            return (
                f"git-guard blocked this call — {label} detected.\n\n"
                f"If this is intentional, re-run with {env_var}=1 set "
                f"and the pre-push git hook will allow it.\n\n"
                f"Pattern matched: /{regex}/"
            )
    return None


def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    **_: Any,
) -> Optional[Dict[str, str]]:
    """Check terminal tool calls for dangerous git patterns."""
    if tool_name != "terminal":
        return None

    if not isinstance(args, dict):
        return None

    command = args.get("command", "")
    if not isinstance(command, str) or not command.strip():
        return None

    block_msg = _check_command(tool_name, command)
    if block_msg is None:
        return None

    return {"action": "block", "message": block_msg}


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    logger.info("git-guard registered: blocking destructive git operations via terminal tool")
