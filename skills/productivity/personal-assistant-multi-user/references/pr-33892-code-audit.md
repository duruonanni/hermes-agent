# Profile Routing Skeleton Audit — 2026-06-02

## Summary
The profile routing skeleton (`target_profile` on `MessageEvent`, `_load_profile_routing()`, `_resolve_profile_for_user()`, routing dispatch block) ships in Hermes v0.15.1 as dead code. Originally proposed in PR #33892, the skeleton was merged upstream but **the downstream consumer was never implemented.**

## What Exists (Merged in v0.15.1)

- `MessageEvent.target_profile: Optional[str]` field in `gateway/platforms/base.py` (lines 1335-1339)
- `GatewayRunner._load_profile_routing()` in `gateway/run.py` (line 3116) — reads `profile_routing` from config.yaml
- `GatewayRunner._resolve_profile_for_user()` in `gateway/run.py` (line 3142) — maps user_id → profile name
- Routing dispatch block in the gateway event handler at `gateway/run.py` line 7098 — sets `event.target_profile`

## What's Missing (Confirmed 2026-06-03 Audit)

**`event.target_profile` is NEVER consumed downstream.** The full trace:

```
inbound message → platform adapter → GatewayRunner._on_event()
  → profile_routing check ✅ sets event.target_profile (line 7109)
  → event.target_profile set but no code reads it
  → AIAgent(...) created with current gateway profile (NO target_profile check)
  → response sent via current gateway identity
```

Confirmed by:
1. Searched entire codebase for reads of `event.target_profile` — only 1 match: the line that SETS it (at `gateway/run.py:7109`). Zero consumers.
2. `_hermes_home` is module-level constant — `get_hermes_home()` called once at import time (line 750), never per-session.
3. `set_hermes_home_override()` exists in `hermes_constants.py` but is never called in the gateway.

## Root Cause Architecture Gap

The gateway process is designed around **one profile per process** (the "separate gateway per profile" model in `multi-profile-gateways.md`). The per-user routing skeleton was merged without the corresponding profile-switching mechanics:

1. Agent initialization code that checks `event.target_profile`
2. Temporary `set_hermes_home_override()` + config reload for the target profile
3. Agent cache isolation per profile (same session key from different profiles must not collide)
4. Profile context restoration after message processing

## Risk

**None.** Dead code with no side effects. Enabling `profile_routing` config is safe but has zero effect — all users still get the current gateway's profile. Safe to leave or remove.

## Audit Methodology

1. Trace data flow: config → `_load_profile_routing()` → `_resolve_profile_for_user()` → `event.target_profile = X` → AIAgent creation
2. Search for reads of `event.target_profile` in entire codebase
3. Search for `set_hermes_home_override()` usage in gateway code
4. Verify `_hermes_home` is module-level constant
5. Check `AIAgent(...)` constructor for any profile-awareness parameters

## Alternative Architecture (Official)

Per `multi-profile-gateways.md`: each profile runs its own gateway process with its own bot tokens, sessions, config. This is the fully implemented and supported approach. Per-user routing within a single gateway was never completed.
