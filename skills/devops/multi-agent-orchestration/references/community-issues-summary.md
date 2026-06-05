# Hermes Community Issues Summary — 2026-06-03

Key GitHub issues relevant to multi-agent orchestration.

## Issue #344 — Multi-Agent Architecture (Umbrella)

**Title:** Feature: Multi-Agent Architecture — Orchestration, Cooperation, Specialized Roles & Resilient Workflows

**Status:** Open, discussion ongoing

**Key points:**
- Current `delegate_task` spawns ephemeral child agents → returns summary → that's delegation, not multi-agent
- True multi-agent needs: specialized roles, structured DAG workflows, inter-agent shared context, resilient execution
- Sub-issues: #356 (Acceptance Criteria), #375 (Inception Prompting), #376 (Adversarial Debate), #377 (Shared Memory Pools)

**Relevance:** Validates the direction of using specialized agents for different tasks. Pipeline pattern is aligned with this vision.

## Issue #9459 — Agent Profiles for delegate_task

**Title:** feat(delegation): agent profiles for delegate_task — custom orchestration harness support

**Status:** Open, proposed

**Key points:**
- Allow config.yaml to define named agent profiles with: system prompt, model, toolset, delegation routing
- Current limitation: all subagents are clones of parent with minimal customization
- Proposed config format:
  ```yaml
  agent_profiles:
    explorer:
      model: google/gemini-2.5-flash
      toolsets: [terminal, file]
    coder:
      model: gpt-5.5
      provider: codex
      toolsets: [terminal, file, web]
  ```
- Would solve: "route codebase exploration to cheap model, architecture to strong model"

**Relevance:** HIGHEST priority for implementation. Would directly enable clean Pipeline routing from Hermes config.

## Issue #476 — Agent Mode System

**Title:** Feature: Agent Mode System — Persona + Tool Scoping + Behavioral Constraints

**Status:** Open, proposed

**Key points:**
- Inspired by Kilocode's Mode System: each mode = persona + tool permission ruleset + behavioral constraints
- Built-in modes: Code (full access), Plan (read-only), Ask (Q&A), Debug (debugging-specific)
- Ruleset = ordered array of {permission, pattern, action} with glob matching

**Relevance:** Would complement Agent Profiles by adding behavioral guardrails per role.
