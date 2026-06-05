# Hermes Hook Architecture Discovery — 2026-06-03

## Context

While evaluating whether code-level enforcement of workflow rules (e.g., "must call `task_analyzer` before generating response") is feasible in Hermes, DS Pro claimed a `before_response` hook exists. This was **false**.

## Actual Hook Architecture

Discovered by searching the Hermes codebase (`model_tools.py`):

| Hook | Location | What it does | Can block tools? |
|------|----------|-------------|-----------------|
| `pre_tool_call` | `model_tools.py:928` | Fires before each tool execution | ✅ Yes — returns block message |
| `post_tool_call` | `model_tools.py:994` | Fires after each tool execution | ❌ Observational only |
| `transform_tool_result` | `model_tools.py:1014` | Can modify tool result text | ✅ Can rewrite output |

## Key Missing Hook

**There is NO `before_response` hook.** When the model generates a final text response (not a tool call), there is no code-level checkpoint. The model decides what to say, and the sentence goes straight to the user. This is the fundamental constraint: you cannot force the model to check a rule before it replies — unless you make the model call a tool first (which DOES fire `pre_tool_call`).

## Practical Implication

To enforce a rule like "analyze task before generating response":

1. Register a `pre_tool_call` Plugin hook via `hermes_cli.plugins.invoke_hook()`
2. If the model tries to call any tool **other than `task_analyzer` first**, block it
3. BUT this only works when the model calls a tool — if the model replies directly without tool calls (simple Q&A), the hook never fires
4. The only way to intercept direct responses is: register a tool that runs on every turn (requires code change to `conversation_loop.py`)

## How to Use

```python
# In ~/.hermes/plugins/my_plugin/__init__.py
from hermes_cli.plugins import register_hook

def check_pre_tool_call(tool_name, tool_args, **kwargs):
    """Block if model tries to skip task_analyzer"""
    if needs_task_analysis(tool_name):
        return {"action": "block", "message": "Please call task_analyzer first"}
    return None

register_hook("pre_tool_call", check_pre_tool_call)
```

## Lesson for Subagent Delegation

When asking subagent models about Hermes-specific architecture:
- They will confidently describe APIs that don't exist (e.g., `before_response`)
- Always verify technical claims against actual code before acting on them
- This applies to: hook names, CLI flags, config keys, API endpoints
