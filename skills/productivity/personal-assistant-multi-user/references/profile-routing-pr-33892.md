# Profile Routing Skeleton (v0.15.1+)

## Status

**Skeleton merged in upstream v0.15.1, but dead code.** The `target_profile` field on `MessageEvent`, the config reader `_load_profile_routing()`, and the dispatch block are ALL shipping in the installed codebase. However, **no downstream code consumes `target_profile`** — setting it has zero effect.

This was originally proposed as PR #33892 by ousiaresearch, and PR #33558 (env var approach) by another contributor. Upstream merged the lighter skeleton (PR #33892's approach) but completed only the config-reading and marker-setting half. The calling-side consumption was never implemented.

## Files Present in v0.15.1 (already shipping, no patch needed)

### gateway/platforms/base.py — MessageEvent (lines 1335-1339)

Added `target_profile` field to MessageEvent dataclass:

```python
# Target Hermes profile override — set by the gateway when profile_routing
# config maps this user to a specific profile.  When set, the gateway
# switches to this profile for the duration of the message processing,
# then restores the original profile afterward.
target_profile: Optional[str] = None
```

**Note:** The docstring says "switches" but the switch logic was never implemented.

### gateway/run.py — Init + Methods (lines 1705, 3116-3151)

**Init** (after `_load_provider_routing()`):
```python
self._profile_routing = self._load_profile_routing()
```

**Static method** — reads `profile_routing` from config.yaml:
```python
@staticmethod
def _load_profile_routing() -> dict:
    try:
        import yaml as _y
        cfg_path = _hermes_home / "config.yaml"
        ...
        return cfg.get("profile_routing", {}) or {}
    except Exception:
        pass
    return {}
```

**Static method** — resolves user_id to profile name:
```python
@staticmethod
def _resolve_profile_for_user(user_id, profile_routing):
    if not user_id or not profile_routing:
        return None
    return profile_routing.get(str(user_id))
```

### gateway/run.py — Routing Dispatch (lines 7094-7109)

```python
# --- Per-user profile routing ---------------------------------------
if self._profile_routing and source.user_id:
    _routed_profile = self._resolve_profile_for_user(
        str(source.user_id), self._profile_routing
    )
    if _routed_profile and _routed_profile != self._active_profile_name():
        logger.info(
            "Profile routing: user %s -> profile '%s' (was '%s')",
            source.user_id, _routed_profile,
            self._active_profile_name(),
        )
        event.target_profile = _routed_profile
```

## What's Still Missing

**No code reads `event.target_profile`.** It's set but never consumed during agent creation. The full chain needed:

1. In the agent creation path (around AIAgent(...) construction), check `event.target_profile`
2. `set_hermes_home_override()` to point at the target profile's root
3. Reload config + resolve provider for the target profile
4. Agent cache key needs profile awareness (same session_key from different profiles must not collide)
5. Restore original profile after message processing

The `set_hermes_home_override()` / `reset_hermes_home_override()` API exists in `hermes_constants.py` but is never called in the gateway.

## Config

In `~/.hermes/config.yaml` (setting this currently has zero effect):

```yaml
profile_routing:
  "ou_33ac860a73d2c8c18203ca55a237881a": default
  "ou_699fbd27d38d19606c83ece40ee21b7d": raya
```

## Pitfalls

- **Dead code, not missing.** Don't tell users to "apply PR #33892 patch" — the skeleton is already there. The missing part is the downstream consumer, which was never implemented.
- **`_hermes_home` is a module-level constant.** Set at gateway import time (`get_hermes_home()` at run.py:750). Cannot be changed per-session without refactoring.
- **Native approach: separate gateways.** The fully supported multi-profile architecture is `multi-profile-gateways.md` — one gateway process per profile, each with its own bot tokens. This requires two Feishu bot tokens for two users.
- **Flat-file segmentation is the pragmatic alternative.** `USER.md`/`MEMORY.md` segmentation (Problem 1 in the parent skill) with `sender.open_id` routing works today, no gateway code changes needed.
