# Multi-Round Debate: Identity Hallucination in Multi-User Hermes

## Context

**Date:** 2026-06-03
**Models:** Hermes Agent (DeepSeek V4 Flash) vs MiMo V2.5 Pro (as opposition)
**Topic:** Solving systematic identity hallucination in a multi-user Hermes Agent setup with Feishu (Lark) as the messaging platform.

**Environment:**
- Two users: Duruo (admin) and Raya (team member)
- Current mitigations: flat-file memory segmentation (`[user:duro]/[user:raya]/[global]`) + `sender.open_id` routing
- Model: DeepSeek V4 Flash
- Hermes v0.15.1

## The Problem

Two types of hallucination:
1. **Knowledge hallucination** — Agent made up the name "xiaomei" for user Raya
2. **Context hallucination** — Agent confused Duruo's conversation history with Raya's

## Debate Structure

| Round | Role | Content |
|-------|------|---------|
| 1 | **Hermes Agent** | Proposed Gateway-layer identity injection via Feishu API + volatile system prompt (2-3 day implementation) |
| 1 | **MiMo (opposition)** | 4-point critique: API dependency risk, memory structure flaw, underestimated cost, better alternative |
| 2 | **Hermes Agent** | Responded to each point: conceded some, rebutted others, corrected timeline to 1 week |
| 2 | **MiMo (rebuttal)** | Deepened critique: cold-start problem, memory correction complexity, recommended model swap first |

## MiMo's Key Arguments

### Round 1
1. **API dependency**: `contact/v3/users/{open_id}` is synchronous blocking on the message path; fails without user authorization
2. **Surface-level fix**: Identity injection is "labeling" not "room-separation"; doesn't help with history recall
3. **Cost underestimated**: Cache policy, error handling, monitoring, cross-platform coupling — missing from estimate
4. **Better path**: Short-term — strengthen `open_id` routing; Long-term — push RFC #31388

### Round 2
1. **Dual-channel adds complexity**: Two fault domains instead of one; cold-start problem for new users
2. **Volatile weight untested**: No consensus that "last-in-context" beats semantic relevance; conflict with MEMORY.md creates race conditions
3. **1 week still optimistic**: Real estimate is 2 weeks minimum
4. **🔑 Model swap first**: DeepSeek V4 Flash hallucination rate ~18% on identity tasks; V3 ~7%; Claude ~3%. Zero-code change to get 75% improvement.

## Outcome

The debate converged on a 4-point action plan:

1. ✅ **Priority 0: Test model swap** — Switch to stronger model (DeepSeek V3 or Claude) before any code changes. Cost: ~zero.
2. ✅ If model swap insufficient, **do small scope** — volatile prompt identity injection only (no memory scanning subsystem)
3. ⏳ **No big refactor** — RFC #31388 and profile routing remain in wait-for-community state
4. ⏳ **Memory fixes ad-hoc** — Scan and correct specific known bad entries manually, don't build a system

## Key Lesson: User Feedback on Debate Format

The user's correction "我看不到Mimo的输出么" revealed a critical workflow rule:

> **When using MiMo for discussion, ALWAYS present the raw API output verbatim. Do NOT summarize or paraphrase.**
> The user needs to see MiMo's actual reasoning, not the agent's interpretation of it.

This is now encoded as a mandatory rule in the `xiaomi-mimo-api` skill's "Multi-Round Debate Pattern" section.
