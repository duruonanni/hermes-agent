---
name: personal-assistant-multi-user
description: >
  Manage multiple users with distinct identities and needs on a shared
  Hermes personal-assistant instance — identify users correctly, isolate
  memory/context per user, handle group-chat blockers, and route reports
  to the right person. Load when a second user joins or when cross-user
  confusion arises.
compatibility: Hermes Agent (Feishu gateway with group_sessions_per_user)
metadata:
  author: duruo
  version: "1.5.0"
  license: MIT
  hermes:
    tags: [assistant, multi-user, identity, management, feishu]
    related_skills: [hermes-agent, hermes-cron-automated-reports, multi-agent-orchestration]
globals: false
---
# Multi-User Personal Assistant

Guide for managing a shared Hermes personal-assistant instance where multiple users (e.g., you + your partner) interact via the same messaging gateway (Feishu, Telegram, etc.).

## ⚠️ FIRST: Verify Premises Before Acting

**Skill files contain TEMPLATE EXAMPLES.** These are NOT user-approved facts. Before you use any content from this skill as a premise for reasoning, delegation, or analysis, you MUST:

1. **Verify the premise against actual files on disk.** Check MEMORY.md and USER.md (and their `memories/` counterparts). Do NOT assume a value exists because you saw it in a skill code block.
2. **Distinguish template from fact.** Code blocks, indented template sections, and bracketed `[user:xxx]` blocks in this skill are EXAMPLES — they were written by a prior agent session, not by the actual users.
3. **Do NOT propagate skill examples into delegation context.** When you delegate to MiMo, DS Pro, or any other model, do NOT include skill template examples as if they were real user preferences. If you must cite them, say "this is from a skill template, needs user confirmation."
4. **If the user corrects you**, verify the actual files immediately. Do not defend.

### Documented Chain Hallucination (2026-06-03)

**Occurrence 1 (early session):** An agent loaded this skill, read the `[user:duro]` and `[user:raya]` template blocks in Problem 1 below, treated them as Duruo's actual preferences, fabricated tone differences between users, and delegated to MiMo + DS Pro for multi-model analysis based on that false premise. Neither user had ever expressed those preferences. **The template blocks in this skill were the sole source.**

**Occurrence 2 (later same day):** A DIFFERENT agent loaded this skill, SAW the WARNING (then on line 121), but still fell into the same trap. Root cause: the agent saw the template examples in Problem 1, thought "these might be real," and the uncertainty eroded into "they probably are." Then it delegated to MiMo + DS Pro — and both models, receiving the false premise in their context, produced detailed analyses based on it. **The error was amplified 3× by the pipeline.**

**Why the warning wasn't enough:** The template `[user:duro]` and `[user:raya]` blocks were still present in the skill. The agent's reasoning went: "the skill says this is an example → but maybe it's based on real data → let me include it in the delegation context for completeness." The mere presence of plausible-looking content in the skill primed the agent to treat it as real.

**Prevention (after Occurrence 2):**
1. This warning is now at the VERY TOP of the skill, before any trigger conditions or problem descriptions.
2. The template examples in Problem 1 have been replaced with generic `[user:USERNAME]` placeholders and marked as templates requiring user confirmation.
3. A runtime rule: **If you are about to delegate a task, review the context for any claims that came from skill template blocks. If in doubt, drop them.**

---

## When This Skill Activates

- A second person joins the shared chat (partner, family, colleague)
- Cross-user confusion occurs (wrong response, mixed-up context, approval stuck in group chat)
- Primary user asks "how do we handle two users?"
- Setting up or troubleshooting multi-user cron delivery

## ⚡ FIRST: Verify Your Premises (Read Before Assuming)

**Before delegating to any other model or asserting any user attribute, stop and verify:**

1. **Skill examples are NOT facts.** Template code blocks, example `[user:xxx]` sections, and suggested workflow diagrams in this skill were written by an Agent session, not by the user. Do NOT treat them as implemented reality.
2. **Check the actual files.** Before saying "USER.md has [user:raya] section" or "the user prefers X tone", read the actual files on disk with read_file. If they don't contain what the skill example shows, the example was not implemented.
3. **Ask the user.** For any personal attribute (tone preference, desired behavior, communication style), ask the user directly. Never infer it from context or skill examples.
4. **If you built a premise on a guess, discard the output.** If you realize mid-analysis that your context contained a fabricated premise, restart. Do not continue the analysis — the output is only valid if the premises are true.

**Known failure (2026-06-03):** An agent read this skill's Problem 1 example blocks (agent-written tone templates), treated them as Duruo and Raya's actual preferences, then delegated to MiMo + DS Pro for a multi-model evaluation based on that false premise. Both models produced detailed analyses of a non-existent problem. The error was only caught when the user asked "这个来源是哪里来的?"

## Core Principle: Honest Identity Handling

### Foundational Rule: Verify Before Asserting

**Never claim something doesn't exist without checking.** If asked "do we have X?" — check the file, the config, the environment — then answer. Saying "no" without looking is the single most common source of user frustration.

This applies to:
- File existence (~/.env, config.yaml, credential files)
- Configuration values (is a feature enabled? Is a key set?)
- Process status (is a service running? Is a port open?)
- Feature availability (does the repo have a desktop app? Does the API support this?)

**Three-step check:**
1. Check the actual source (file read, terminal, API call)
2. Verify the result is current (not stale cache)
3. Answer with evidence: "checked ~/.hermes/.env: FEISHU_APP_ID is set to cli_xxx"

Exception: if the tool to check is unavailable (network down, no sudo), say "I can't verify because [reason]" — don't default to "it's not there."

### Foundational Rule: Read Before Executing

When the user sends a multi-part message, read and acknowledge ALL parts before running any tool.

**Sequence:**
1. Read the user's entire message
2. Parse each request/question mentally
3. Acknowledge key points briefly in your response
4. Then execute tools

**Known failure mode:** User sent a long message with a question + a Kanban update + "把codex停了吧". The agent ran the Kanban command and reported the result, but never addressed the user's other content. User replied: "这个消息你没回."

**Rule:** One tool call that produces an opaque status block without framing it in the user's context does NOT count as a response. Every response must first show you understood the user's message, then present results in that context.

### Session Re-Entry: Always Confirm Identity First

When a session expires and a new one starts, you lose identity context. Do NOT assume you are talking to the same person from the previous session — especially in multi-user setups.

**Protocol:**
1. Before referencing ANY content from past sessions, verify who you are talking to
2. Cross-check the current sender's open_id against stored identities
3. If the open_id does not match a stored user: "I see a new session started — could you confirm who I am talking to?"
4. Only reference past session content if it belongs to the confirmed current user
5. Never summarize multi-user past conversations generically — you will mix up whose topics belong to whom

**Known failure case:** After Raya said goodnight in a session, Duruo started a new session. The agent summarized "we talked about skill audits and GitHub Issues" — which were Duruo's topics, not Raya's. Root cause: session expired, new user began, agent did not check who was talking.

**You cannot recognize a user by their platform ID alone.** A Feishu open_id (e.g., `ou_699fbd27d38d19606c83ece40ee21b7d`) is an opaque hash — it distinguishes *that there are two different users*, but it does not tell you *who they are*.

- ✅ **You can say**: "I see two different open_ids, so these are different people."
- ❌ **Never claim**: "I recognize her" or "I can identify who this is."
- ❌ **Never fabricate** a user's name, role, or identity from an open_id.
- ✅ **Right approach**: "I found this open_id in the logs — is this your girlfriend? If so, save it and I'll know next time."

### User Registration Pattern

### Actual Identities (stored 2026-06-01)

Primary user: **Duruo** — technical background, Lenovo BA, NUC operator
Secondary user: **Raya (雷环瑜 / Lei Huanyu)** — 28yo, 四川南充, 7yr construction cost engineer (土建+精装+泛光)
  - 西南科技大学 建筑经济管理 本科
  - 持有：二级建造师(建筑)、中级职称、安考B证、资料员证
  - 技能：广联达, 宏业, CAD
  - 在成都求职，在职至2026.05 于四川新文行建设工程有限公司
  - 代表项目：成都三圣乡精装工程（合同价~5000万）
  - 沟通模式：谨慎阅读再回复（"我先看看"），偏好详细数据化建议
  - 飞书 open_id: ou_699fbd27d38d19606c83ece40ee21b7d

### Registration Pattern

When a primary user introduces a secondary user:

1. **Get a distinguishing signal**: Ask the primary user to have the secondary user send a DM to the bot, OR ask the primary user to confirm the open_id explicitly.
2. **Save both open_ids to memory**: Store primary user and secondary user identities in `memory` target (for open_ids) and `user` target (for primary user preferences).
3. **Associate context**: Save what the secondary user needs (e.g., "job-seeking," "warm responses," "help with X").
4. **Verify after setup**: After saving, explicitly confirm with the primary user that the open_id is correct. Say something like: "I've saved her open_id now — next time she sends a message, I'll know it's her."

## Problem 1: Memory Conflict — User-Specific Voices

**Symptom:** Both users' preferences are in the same MEMORY.md/USER.md. Without per-user voice sections, the agent defaults to a single persona for everyone.

**⚡ User preference (stated 2026-06-03):** Duruo explicitly said "我不认为我和Raya需要你提供不一样的语气". They do NOT want per-user tones. The default Hermes persona ("helpful, knowledgeable, direct") is sufficient for both users. Do NOT assume different users need different voices unless they explicitly ask.

**⚠️ READ THE "FIRST: Verify Premises" section at the top of this skill before using the templates below.**

**Solution: USER.md Segmentation (Process, Not Template)** (template — requires user CONFIRMATION before writing; do NOT assume any user wants different voices unless they explicitly ask)

```
§
[user:USERNAME]
# USER-CONFIRMED preferences go here
# Do NOT fill from agent assumptions — ask the user first
§
[user:USERNAME]
# USER-CONFIRMED preferences go here
```

**Runtime rule for the agent:** 
- Never assume a user's preferred voice exists — check actual USER.md/MEMORY.md on disk (they are usually empty for voice preferences)
- Never propagate voice/style preferences from skills into your reasoning — skill examples are templates, not facts
- Per-user voice is OPT-IN. Do NOT create per-user voice sections unless the user explicitly asks
- Default to Hermes's default persona for ALL users

### What NOT to Do

- **Do NOT** create separate memory files per user (Hermes doesn't support conditional file loading)
- **Do NOT** try to guess the user from message content (names in text can be misleading)
- **Do NOT** switch voice mid-conversation — commit to the active user's style for the entire turn

## Problem 2: Group Chat Approval Prompts

**Symptom:** In a Feishu group chat, the agent fires an approval prompt. The approval button is embedded in the last message card. The secondary user (or any group member) cannot see or interact with this button. All subsequent @mentions are ignored because the session is blocked waiting for approval.

**Solution: Platform-Aware Approval Policy**

Apply different approval rules by channel type:

| Channel | Low-risk (read, query) | Medium-risk (modify config) | High-risk (delete, restart) |
|---------|----------------------|---------------------------|---------------------------|
| **DM** | Normal approval flow | Normal approval flow | Normal approval flow |
| **Group chat** | Auto-approve (silent) | Auto-reject + reply "这个操作需要私聊我" | Auto-reject + warning |

**Time-based fallback (all channels):** If approval is not answered within **60 seconds**, auto-reject and release the session. This prevents permanent blocking.

**Post-block recovery:** If a session is already blocked (user says "it's stuck"):
1. Tell the user to DM the agent directly
2. In DM, the approval prompt renders correctly
3. The user can approve/reject there

## Problem 3: Context Cross-Contamination

**Symptom:** User A asks a question in the group chat. Then User B @mentions the bot with an unrelated question. The agent references User A's question in its response to User B, mixing contexts.

**Root cause:** Hermes `group_sessions_per_user=true` creates per-user session isolation, but the agent's system prompt includes the full group chat's recent message history. This allows cross-user context to leak in.

**Solution: Metadata-First Context Filtering**

Add a strict rule at the top of every response in group chats:

> **When responding in a shared group chat:**
> - Only consider messages sent by the CURRENT sender (identified by open_id)
> - Ignore messages from other users in the same group — they belong to a different session
> - Do NOT reference, summarize, or build upon messages from other users
> - The sender's own message history is the only valid context

This rule goes in the agent's active mental model (NOT as a skill to load — it's a runtime behavior rule embedded in memory and reinforced by this skill).

## Problem 4: Identity Confusion Despite Stored IDs

**Symptom:** Both open_ids are saved in memory. But in group chat, the agent still confuses who sent a message — especially when someone mentions a name ("tell Duruo that...").

**Solution: metadata-first, every time**

**Always check the sender's open_id from the event payload before responding.** Never infer the sender from message text content.

```python
# Pseudocode: correct identity resolution
def resolve_sender(event):
    # 1. The ONLY trusted source
    open_id = event.sender.open_id
    
    # 2. Look up in memory
    if open_id == "ou_xxx": return "duro"
    if open_id == "ou_yyy": return "raya"
    
    # 3. Unknown — don't guess
    return None
```

Add this to the agent's runtime behavior (from memory):

> **用户身份以系统提供的 open_id 为准，不要根据消息文本中的名字来判断发言人。**

### Verifying Who Sent a Past Message

When the user says "that message wasn't from me" or "who said that in the group":

```bash
grep "text='关键短语'" ~/.hermes/logs/gateway.log
```

This shows `sender=user:ou_xxx` — compare against stored identities. Do NOT reason from context or guess.

### Real-World Failure: Group Sender Confusion

**Scenario:** Secondary user (girlfriend, open_id B) sent in group chat: "你可以给Duruo说我不想去爬楼梯吗". Later asked about this, the agent assumed it was from the primary user (Duruo, open_id A) because "the group chat is with Duruo."

**Root cause:** Memory had both IDs saved, but the agent did NOT re-check the sender open_id of the original message. Memory is necessary but not sufficient — every assertion about who said what must be verified against the gateway log.

### Real-World Failure: Third-Party Model Name Fabrication

**Scenario:** The agent asked MiMo (mimo-v2.5-pro) to analyze multi-user architecture options. MiMo's response used "[user:xiaomei]" as a placeholder name for Raya. The agent copied this placeholder into its reply to Duruo without cross-checking against stored identities. Duruo immediately corrected: "等等 为什么叫她 xiaomei, 这个依据是哪里来的."

**Root cause:** The agent trusted an external model's output over its own stored data. USER.md contained Raya's full name (雷环瑜 / Lei Huanyu / Raya) with open_id. The agent should have caught "xiaomei" as a mismatch before ever using it.

**How to avoid:**
1. Before citing any user-identifying information (name, role, preference) from a third-party model's output (MiMo, GPT, etc.), cross-check against USER.md and MEMORY.md
2. If the external model uses a name that doesn't match any stored record, discard it and use the real name
3. Never use placeholder names from model responses — they are training data artifacts, not real identities
4. This error compounds: once a fake name appears in a skill or memory, every future session propagates it

## Problem 5: Skill Role Filtering

**Symptom:** Administrative skills (nuc-server-maintenance, linux-system-relocation) load alongside general skills even when the secondary user is asking about job hunting, wasting context.

**Solution:** Use skill tags and load contextually.

- **Admin-only skills** (tags: `[admin, infra]`): nuc-server-maintenance, linux-system-relocation, hermes-gateway-platforms, hermes-dashboard
- **General skills** (tags: `[general]`): personal-assistant-multi-user, html-to-pdf, feishu-document-api, ocr-and-documents, deepseek-api, xiaomi-mimo-api
- **Her-only skills** (tags: `[raya]`): (none yet, but career-coaching could go here)

When responding to the secondary user, skip admin-tagged skills from the initial scan. Only load them if the conversation explicitly steers there.

## Problem 6B (Advanced): Per-User Profile Routing

**Symptom:** USER.md segmentation (Problem 1) works but shares the same char limit,
has no query structure, and relies on fragile text parsing. For true isolation
— separate memories, skills, configs, and cron jobs per user — you need
profile routing.

**Solution: Hermes v0.15.1+ has a profile routing skeleton merged upstream, but
it's DEAD CODE — `target_profile` is set on events but never consumed during
agent initialization.** The intended flow is:

Add a `profile_routing` block to config.yaml mapping user IDs to profile names:

```yaml
profile_routing:
  "ou_33ac860a73d2c8c18203ca55a237881a": default
  "ou_699fbd27d38d19606c83ece40ee21b7d": raya
```

The gateway routes inbound messages to the target profile before building
the agent context. **BUT** — this is aspirational. The skeleton exists (sets
`event.target_profile`) but no code actually switches the Hermes home or
creates a different-context agent.

### What Already Ships (v0.15.1)

- `MessageEvent.target_profile: Optional[str]` field in `gateway/platforms/base.py` (line 1335)
- `_load_profile_routing()` — reads `profile_routing` from config.yaml (`gateway/run.py:3116`)
- `_resolve_profile_for_user()` — maps user_id → profile name (`run.py:3142`)
- Routing dispatch block — sets `event.target_profile` on matched events (`run.py:7098`)

### What's Missing

- **No code reads `event.target_profile` during agent creation** — verified by searching the entire codebase
- `_hermes_home` is a **module-level constant** — set once at `run.py:750` via `get_hermes_home()`, never changes per-session
- `set_hermes_home_override()` exists in `hermes_constants.py` but is never called in the gateway
- No agent cache key that incorporates profile name (same session_key from profile A and profile B would collide)

### Implementation Needed

To complete this feature, the gateway event handler that creates/retrieves the
`AIAgent` instance would need to:

1. Check `event.target_profile` before creating the agent
2. Call `set_hermes_home_override(profile_path)` to point at the target profile's root
3. Reload config.yaml for the target profile (different model, provider, skills)
4. Create the AIAgent with the target profile's config
5. Restore with `reset_hermes_home_override(token)` after response

### When to Use Profile Routing vs. USER.md Segmentation

**Start with USER.md segmentation (Problem 1) — Profile Routing when:**
- A third user joins
- Cross-user memory conflicts become untenable
- You need per-user cron isolation
- You're willing to implement ~50 lines of gateway code

**Setup time:** USER.md = 15 min (edit file). Profile routing = unknown
(the feature skeleton is shipping but non-functional — no known working
implementation exists publicly).

**Scaling:** USER.md tops out at ~2-3 users. Profile routing scales to many,
but requires a platform with separate bot tokens per instance, or the
unfinished per-user routing code above.

**Alternative that works today:** Run separate gateway processes, each with
its own Feishu bot token. See `multi-profile-gateways.md`.

See `references/pr-33892-code-audit.md` for the full audit (confirmed dead code).
See `references/profile-routing-pr-33892.md` for skeleton details.
See `references/error-pattern-audit.md` for documented failure patterns and their fixes.

## Problem 7: Cron Report Delivery to Multiple Users

**Symptom:** All cron reports currently deliver to the primary user's DM. The secondary user never sees reports, even reports relevant to them.

**Solution:** Configure cron jobs with explicit `deliver` to the appropriate chat:

```python
# System reports → primary user only
cronjob(
    action='create',
    name='nuc-health-check',
    schedule='0 8 * * *',
    deliver='feishu:oc_PRIMARY_DM',  # Duruo only
    ...
)

# Job market reports → secondary user (Raya)
cronjob(
    action='create',
    name='job-market-brief',
    schedule='0 9 * * 1-5',
    deliver='feishu:oc_RAYA_DM',  # Raya only
    ...
)

# Summary reports → both (in group)
cronjob(
    action='create',
    name='weekly-summary',
    schedule='0 10 * * 1',
    deliver='feishu:oc_GROUP_ID',  # group chat
    ...
)
```

To find the chat IDs: the cron job's `origin` field in the list output shows `chat_id` for each origin. The user's DM chat_id and the group chat_id are different.

## Identifying Users in Gateway Logs

The gateway log labels inbound messages with both the chat_id and the sender's open_id:

```
[Feishu] Inbound dm message received: id=om_xxx ... chat_id=oc_AAA sender=user:ou_xxx1 text='hello'
[Feishu] Inbound dm message received: id=om_yyy ... chat_id=oc_BBB sender=user:ou_xxx2 text='hi'
```

- **Different `sender=user:ou_xxx`** → different users (even if chat_id is the same, e.g., in a group chat)
- **Different `chat_id`** → different conversations (DM vs group, or different users' DMs)
- **`chat_type=group` vs `chat_type=p2p`** → group chat vs DM

On the Hermes side, the gateway creates **per-user session contexts** even in shared group chats (`group_sessions_per_user: true`). So messages from different users in the same group are processed in isolated sessions.

## Channel Awareness (Feishu)

Users may interact via **DM** (private chat with bot) or **group chat**:

- **DM messages**: Always processed — no @mention needed.
- **Group messages**: Only processed when `@机器人名字` is used (controlled by `FEISHU_REQUIRE_MENTION`, defaults to `true`).
- **Each channel is independent**: DM session context ≠ group chat session context, even for the same user.

## Research Methodology Preference

When the primary user (Duruo) asks you to research a topic, look up documentation, or verify claims:

1. **Prioritize official/primary sources first**: GitHub repos (README, docs/), official websites, API documentation, vendor docs. These are the authoritative source.
2. **Prefer community-maintained spec repos over blog posts**: e.g., the `agentskills/agentskills` GitHub repo for agentskills.io spec, or the `NousResearch/hermes-agent` repo for Hermes docs.
3. **Chinese blog posts/third-party summaries are fallback only**: Use them when official docs are paywalled, inaccessible (site blocked), or don't exist. Do NOT lead with them.
4. **When in doubt, check the official GitHub repo**: Search the repo's code/docs via the GitHub API or `site:github.com` search before going to general web search.
5. **Cite sources by origin**: "From the agentskills.io spec (github.com/agentskills/agentskills)" rather than "found on a website."

This preference was established after the user corrected: "你web Search 尽量查官网和官方社区信息哈" (2026-06-02).

## Memory Organization

Keep user profiles compact by removing duplicates:

```
MEMORY.md: "用户女朋友 雷环瑜 (Raya)：飞书 open_id = ou_699fbd27d38d19606c83ece40ee21b7d。工程造价求职中成都。热情回复多帮忙。"
USER.md:   "Duruo — 我的主要用户。飞书 open_id = ou_yyy。技术熟悉联想BA。回应中文。"
```

Do NOT store session-specific details (task state, what you said last) in memory — store those in the session transcript and retrieve via `session_search`.

## Priority Matrix (from MiMo v2.5 Pro Analysis)

When triaging multi-user issues, use this priority order:

- **🔴 High** — Memory/voice conflicts, approval blocking, context contamination
- **🟡 Medium** — Identity confusion, skill loading waste
- **🟢 Low** — Cost contention, cron routing


See `references/pr-33892-code-audit.md` for the full audit (confirmed dead code).
See `references/profile-routing-pr-33892.md` for skeleton details.
See `references/error-pattern-audit.md` for documented failure patterns and their fixes.

## Upgrade Paths: When Section-Based Memory Breaks

The section-based approach (Problems 1-4) is the right starting point but has a bounded lifecycle. This section documents the degradation trajectory, risk signals, and concrete upgrade options so you can plan before the approach breaks.

### Degradation Timeline (2-User Scenario)

| Time | Status | Risk |
|------|--------|------|
| Month 0 (deploy) | ✅ Works | Clean sections, correct routing |
| Month 1 | ✅ Still works | Agent remembers to check open_id consistently |
| Month 2 | ⚠️ Occasional confusion | Agent delivers wrong-user responses ~5-10% of turns |
| Month 3 | ❌ Unreliable | USER.md at 80-90% capacity; compression loses section granularity |
| Month 4+ | ❌❌ Must upgrade | Drift detection prevents memory writes; user correction fatigue |

Drivers of decay:

- **Capacity pressure:** USER.md defaults at 1375 chars; even at the user-expanded 2500 limit, two full profiles with preferences leave ~300-500 chars of headroom. Weekly growth of ~400 chars means 4-6 weeks from 80% to full.
- **Agent confusion:** As sections compress, distinguishing cues degrade. The agent starts mixing responses — Duruo's technical detail delivered to Raya, Raya's warm style applied to Duruo.
- **Drift detection:** Once the file exceeds char_limit (naturally or via compression), the memory tool's `_detect_external_drift()` refuses writes, saving `.bak` files each time and requiring manual recovery.

### Risk Signals — Act on Any One

- 🔴 USER.md or MEMORY.md usage exceeds 80% of char_limit
- 🔴 Any user says "you gave me the wrong person's info" or "this wasn't for me"
- 🟡 Agent uses one user's name/voice/style when responding to the other
- 🟡 User reports "you forgot my name" or "why are you talking to me like this"
- 🟡 A third user wants to join the instance

### Upgrade Cost-Benefit Matrix

| Path | What It Does | Dev Cost | Risk | User Capacity | Reversibility |
|------|-------------|----------|------|--------------|---------------|
| **Plugin isolation** | `pre_gateway_dispatch` + `pre_llm_call` hooks swap memory blocks per user before LLM call | 2-4h dev | Low (no core code changes) | ~5 users | ✅ Delete plugin dir + restart gateway |
| **Gateway routing** | Patch `gateway/run.py` to switch `HERMES_HOME` per user_id before AIAgent init (~50 lines to connect the existing `event.target_profile` skeleton) | 4-8h + PR | Medium (core code) | ~10 profiles | ⚠️ PR merge needed first to revert |
| **Multi-process** | Run separate gateway processes, each with own bot token + profile | 30min config | Low (fully independent) | Unlimited | ✅ Stop extra process |

### When to Choose Which

- **Plugin:** Best for 2-3 users on a single gateway. No core changes, worst case is restore a plugin dir. **Architectural cost:** each `pre_llm_call` hook execution must scan and modify the messages array, which breaks the MemoryStore frozen-snapshot design — the provider's prefix cache is invalidated on every turn, costing ~2-5K extra tokens per LLM call (~$1-3/day for 100 conversations). Acceptable for 2-3 users; painful at 5+.

- **Gateway routing:** Best for 3-10 users. One-time switch at AIAgent creation — zero per-turn overhead. The skeleton is already merged upstream (`event.target_profile` is set in the dispatch path but never consumed — verified dead code as of v0.15.1). Estimated ~50 lines to connect the skeleton: read `event.target_profile` before AIAgent init, call `set_hermes_home_override(profile_path)`, and restore after response.

- **Multi-process:** Best for 10+ users or when upstream changes can't wait. Each process is fully independent — separate memory, skills, config, cron. Resource cost is ~2GB RAM per process; each needs its own messaging platform bot token.

### Architecture Risks That Apply to ALL Shared-Gateway Paths

1. **External memory provider blind spot (Plugin + Gateway routing only):** Hermes supports external memory providers (Honcho, Mem0, Supermemory) via `MemoryManager.build_system_prompt()`. The system prompt builder appends BOTH `_memory_store.format_for_system_prompt()` (the section-based files) AND `_memory_manager.build_system_prompt()` (external provider output). Plugin isolation that only swaps the file-based block still leaks external provider content to the wrong user. To fully isolate, you must also disable or filter the external memory provider per user.

   ```python
   # system_prompt.py volatile tier — both sources injected at every turn:
   volatile_parts.append(mem_block)           # _memory_store — Plugin can intercept
   volatile_parts.append(user_block)          # _memory_store — Plugin can intercept
   volatile_parts.append(ext_mem_block)       # _memory_manager — Plugin CANNOT intercept!
   ```

2. **Group chat cross-contamination (all shared-gateway paths):** `group_sessions_per_user=True` creates per-user session isolation at the transcript level, but the system prompt (and therefore memory) is shared across all users of the same gateway process. If User A's memory is loaded while processing User B's message — because the session_key derives from `chat_id+thread_id`, not from `sender.user_id` in certain edge cases — cross-user memory leaks occur.

   **Mitigation:** In group chats, the agent must confirm `event.sender.user_id` before referencing user-specific memory. If the sender's open_id doesn't match the stored identity, fall back to generic responses until identity is confirmed.

### Decision Framework

```
How many users?
├── 1       → No action needed (default Hermes)
├── 2-3     → Section-based (Problems 1-4) + monitor capacity
│             If confusion appears → Plugin isolation
├── 3-10    → Skip Plugin, go direct to Gateway routing
│             The per-turn prefix-cache cost of Plugin compounds badly
└── 10+     → Multi-process or dedicated per-user infrastructure
```

## Pitfalls

- **Don't treat skill example blocks as implemented fact.** Skill files contain template examples (marked with code blocks or indented text). These are NOT actual MEMORY.md/USER.md content. Before asserting any user preference, voice, or style, verify the actual memory files on disk. Known failure: an agent read `[user:duro]` example blocks from this skill, treated them as Duruo's actual preferences, and fabricated a multi-model analysis based on them. Skills are guides, not configuration files.
- **Don't treat different chat_ids as the same user.** The same user has one open_id but may have multiple chat_ids (DM chat, group chat). Conversely, different users in a group share the same group chat_id but have different sender open_ids.
- **Remember to `/reset` after changes.** Toolset changes (enabling feishu_doc, etc.) don't apply mid-session.
- **Approval in group chat = invisible.** The secondary user cannot approve prompts in group. Default to auto-reject and redirect to DM.
- **Don't over-split USER.md.** Two voice sections is enough. More than 3 and the agent will struggle to match correctly.
- **Cron delivery to a user's DM requires knowing their chat_id.** The chat_id is NOT the same as open_id. Find it via `cronjob action=list` on an existing job created from that user's DM, or ask the user to send a message and grep the gateway log.
- **Metadata-first identity is a runtime rule, not a memory entry.** It must be reinforced in the agent's active reasoning, not just "saved somewhere."
- **Do NOT propagate third-party model name fabrications.** When using MiMo, GPT, or any external model for analysis/consultation, the model may invent names for your users (e.g., MiMo invented "xiaomei" as a placeholder name for Raya). Always cross-check generated names against actual stored identities (USER.md, MEMORY.md) before using them. If the fabricated name doesn't match any stored record, discard it and use the real name. This error compounds — once "xiaomei" appears in a skill, every future session will propagate it.
- **Don't say "doesn't exist" without checking.** Before claiming a file, config key, or feature is absent, verify with a tool call. The FEISHU_APP_ID was set but the agent said it wasn't — one `grep ~/.hermes/.env` would have prevented it.
- **Don't skip the user's content to run tools.** When the user sends a multi-part message, acknowledge their full message first. Running a tool and reporting its output without framing it in their context is indistinguishable from a bug.
