# Premise Gate Pattern — Pipeline Error Amplification Prevention

## Problem

When the orchestrator delegates to multiple models in sequence (MiMo → DS Pro → aggregation), any error in the initial context is amplified:

- A false premise in the orchestrator's context gets passed to MiMo
- MiMo's analysis validates that premise (because it received it as given)
- DS Pro's architecture analysis builds on the same false premise
- Result: three models produce consistent but wrong output

## The Pattern

Add a **premise gate** before the first delegation:

1. Extract all factual claims from your context
2. Verify each claim against actual files on disk (USER.md, MEMORY.md, config.yaml, etc.)
3. Only claims that pass verification enter delegation context
4. Tag verified claims with a note in the context

## Practical checklist before delegation

- [ ] Every claim about user preferences checked against USER.md/MEMORY.md on disk
- [ ] Every claim about config/state verified via terminal or file read
- [ ] No content from skill template blocks used as fact
- [ ] If unsure, include a disclaimer: "this is from a skill template, needs verification"

## Known Failure (2026-06-03)

The orchestrator loaded `personal-assistant-multi-user` skill, saw `[user:duro]` template blocks with fabricated tone preferences, treated them as real, and passed them into the delegation context for MiMo + DS Pro. Three models independently produced analysis confirming a problem that didn't exist. Fix: premise gate at top of orchestration flow.
