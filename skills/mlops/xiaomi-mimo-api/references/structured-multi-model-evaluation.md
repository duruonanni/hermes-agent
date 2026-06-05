# Structured Multi-Model Evaluation

Use when you need to evaluate agent configuration content (MEMORY.md, USER.md, SKILL.md, proposals) using multiple models in parallel for cross-validation.

## When to Use

- User asks to "review" or "evaluate" content
- Before replacing USER.md or MEMORY.md with a generated alternative
- When you need a second-opinion on a plan, strategy, or architecture
- When comparing a Copilot/AI-generated output against the actual source material

## Methodology

### Step 1: Define evaluation dimensions

Standard 6-dimension framework:

1. **Accuracy** — Does it correctly capture reality? Flag overclaims (assertions not in source), contradictions, and misinterpretations.
2. **Completeness** — Is anything important missing from the source? Compare both directions.
3. **Structure** — Is the organization logical? Are critical items prominent? Flat list vs sectioned hierarchy?
4. **Actionability** — Can the agent follow each rule concretely? Or are some too abstract / subjective?
5. **Size / Cost** — For injected content: is the token cost justified? What can be trimmed?
6. **Recommendations** — Prioritized action list (P0/P1/P2). What to merge, remove, or move.

### Step 2: Prepare the evaluation prompt

Feed both pieces of content (current + proposed, or target + criteria) into a single self-contained prompt. Include the 6 dimensions as evaluation instructions.

```python
eval_prompt = f"""You are an expert evaluator...
[CURRENT CONTENT]
...
[PROPOSED/NEW CONTENT]
...

Evaluate across these dimensions:
1. ACCURACY - ...
2. COMPLETENESS - ...
3. STRUCTURE - ...
4. ACTIONABILITY - ...
5. SIZE/COST - ...
6. RECOMMENDATIONS - ...
"""
```

### Step 3: Run models in parallel

Call DeepSeek V4 Pro and MiMo V2.5 Pro with the **same prompt**:

```python
# Parallel calls
ds_result = call_model("deepseek-v4-pro", ds_key, "https://api.deepseek.com", ...)
mimo_result = call_model("mimo-v2.5-pro", mimo_key, "https://token-plan-cn.xiaomimimo.com/v1", ...)
```

### Step 4: Synthesize results

Compare both outputs for:
- **Consensus** — Both agree → high confidence finding
- **Disagreement** — Each sees different issues → dig deeper
- **Unique insight** — One model caught something the other missed → flag it

### Step 5: Present as structured summary

Format:
```
**Consensus findings:**
- Point 1 (both said)
- Point 2

**Disagreements:**
- Point X | Model A says... | Model B says...

**Unique observations:**
- Model A noticed...
- Model B noticed...

**Recommendation:**
- P0: ...
- P1: ...
- P2: ...
```

## Pitfalls

- **Model can influence the eval.** DeepSeek V4 Flash (day-to-day model) may have different reasoning style from MiMo V2.5 Pro. This is by design — you want independent perspectives, not agreement.
- **Token cost.** Each evaluation is ~4-8K tokens per model call. DeepSeek V4 Pro ¥3/M input + ¥6/M output ≈ ¥0.03-0.06 per evaluation. MiMo V2.5 Pro ¥6/M flat ≈ ¥0.03-0.05 per. Acceptable for infrequent quality checks.
- **Don't average.** When models disagree, do not compromise by averaging their positions. Present the disagreement to the user — they decide.
- **Context isolation is critical.** Each model call must be a self-contained prompt with all context embedded. Sub-agent calls have no access to your current session.
