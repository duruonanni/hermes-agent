"""Connect Codex per-operation approvals to Hermes' existing human surfaces."""


def resolve_codex_approval_callback():
    from tools import approval_context
    from tools.terminal_tool import _get_approval_callback

    if approval_context._no_user_can_answer():
        return None
    if approval_context._is_gateway_approval_context():
        return _gateway_codex_approval
    return _get_approval_callback()


def _gateway_codex_approval(command: str, description: str, **_kwargs) -> str:
    from agent.redact import redact_approval_display
    from tools.approval_prompt import request_elicitation_consent

    # No remember_key: this authorizes only this request, never a session or a future command.
    decision = request_elicitation_consent(
        redact_approval_display(command), redact_approval_display(description),
        surface="gateway", title="Approve this Codex operation?",
    )
    return {"accept": "once", "decline": "deny", "cancel": "cancelled"}.get(decision, "deny")
