"""A gateway human, not notifier absence or a stale CLI panel, decides Codex operations."""
import pytest

from agent.codex_approvals import resolve_codex_approval_callback
from agent.transports.codex_app_server_session import CodexAppServerSession
from tools import approval, approval_context


@pytest.mark.parametrize("choice, expected", [("once", "accept"), ("deny", "decline")])
@pytest.mark.parametrize("operation", ["exec", "file-change"])
def test_gateway_approval_round_trip(monkeypatch, choice, expected, operation):
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "feishu")
    monkeypatch.setattr(approval_context, "_is_single_query_approval_context", lambda: False)
    monkeypatch.setattr(approval_context, "_is_cron_approval_context", lambda: False)
    monkeypatch.setattr(approval_context, "_get_approval_timeout", lambda: 1)
    session_key = "test-codex-gateway"
    token = approval_context.set_current_session_key(session_key)
    prompts = []

    def notify(data):
        prompts.append((session_key, data))
        approval.resolve_gateway_approval(session_key, choice)

    approval.register_gateway_notify(session_key, notify)
    try:
        callback = resolve_codex_approval_callback()
        session = CodexAppServerSession(model="test-model", cwd="/", approval_callback=callback)
        if operation == "exec":
            decision = session._decide_exec_approval({"command": "browser-check", "cwd": "/"})
        else:
            decision = session._decide_apply_patch_approval({"reason": "update test fixture"})
        assert decision == expected
        assert len(prompts) == 1
        assert prompts[0][0] == session_key
        assert prompts[0][1]["command"]
        assert prompts[0][1]["allow_session"] is False
        assert prompts[0][1]["allow_permanent"] is False
    finally:
        approval.unregister_gateway_notify(session_key)
        approval_context.reset_current_session_key(token)


def test_gateway_without_listener_denies(monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "feishu")
    monkeypatch.setattr(approval_context, "_is_single_query_approval_context", lambda: False)
    monkeypatch.setattr(approval_context, "_is_cron_approval_context", lambda: False)
    token = approval_context.set_current_session_key("no-codex-listener")
    try:
        callback = resolve_codex_approval_callback()
        assert callback("browser-check", "Approve browser check") == "deny"
    finally:
        approval_context.reset_current_session_key(token)


@pytest.mark.parametrize("mode, expected", [("timeout", "cancelled"), ("send-failure", "deny")])
def test_gateway_unanswered_requests_never_run(monkeypatch, mode, expected):
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "feishu")
    monkeypatch.setattr(approval_context, "_is_single_query_approval_context", lambda: False)
    monkeypatch.setattr(approval_context, "_is_cron_approval_context", lambda: False)
    monkeypatch.setattr(approval_context, "_get_approval_timeout", lambda: 0)
    key = "codex-unanswered"
    token = approval_context.set_current_session_key(key)

    def notify(_data):
        if mode == "send-failure":
            raise RuntimeError("approval surface unavailable")

    approval.register_gateway_notify(key, notify)
    try:
        assert resolve_codex_approval_callback()("browser-check", "Approve once") == expected
        assert not approval.has_blocking_approval(key)
    finally:
        approval.unregister_gateway_notify(key)
        approval_context.reset_current_session_key(token)


@pytest.mark.parametrize("kind", ["single-query", "cron", "webhook"])
def test_unattended_contexts_keep_failing_closed(monkeypatch, kind):
    monkeypatch.setenv("HERMES_SESSION_PLATFORM", "webhook" if kind == "webhook" else "feishu")
    monkeypatch.setattr(approval_context, "_is_single_query_approval_context", lambda: kind == "single-query")
    monkeypatch.setattr(approval_context, "_is_cron_approval_context", lambda: kind == "cron")
    assert resolve_codex_approval_callback() is None
