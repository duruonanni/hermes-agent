#!/usr/bin/env python3
"""Verify that created skill files exist and are non-empty."""
import os

base = os.path.expanduser("~/.hermes/skills/mlops/xiaomi-mimo-api")

ref_path = os.path.join(base, "references/structured-multi-model-evaluation.md")
if os.path.exists(ref_path):
    size = os.path.getsize(ref_path)
    print(f"✅ references/structured-multi-model-evaluation.md ({size} bytes, {size // 1024} KB)")
else:
    print("❌ ref file MISSING")

skill_path = os.path.join(base, "SKILL.md")
if os.path.exists(skill_path):
    with open(skill_path) as f:
        content = f.read()
    if "Structured Multi-Model Evaluation" in content:
        print("✅ SKILL.md has pointer to the new reference")
    else:
        print("❌ SKILL.md missing the pointer")
else:
    print("❌ SKILL.md MISSING")

print("\nDone.")
