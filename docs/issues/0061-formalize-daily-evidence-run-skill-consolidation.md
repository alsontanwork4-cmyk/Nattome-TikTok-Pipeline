# Formalize Daily Evidence Run Skill Consolidation

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/daily-evidence-run-skill-consolidation-prd.md`

## What To Build

Formalize the Nattome skill setup so normal operation uses one Daily Evidence Run skill, while discovery and evidence-analysis phase skills remain supporting references for debugging and reruns.

The current user-facing language should describe daily top-5 operation only. Weekly/default-batch/deep-run language should not appear as a current normal workflow in skills or high-level docs. Shared reference documents should remain the source of truth for Nattome brand voice, claim guardrails, virality analysis, and domain terms.

## Acceptance Criteria

- [ ] The primary Daily Evidence Run skill is the only normal user-invocable skill.
- [ ] The discovery phase skill is marked as a supporting reference and is not a normal user entry point.
- [ ] The evidence-analysis phase skill is marked as a supporting reference and is not a normal user entry point.
- [ ] The primary skill documents the daily discovery command, daily evidence command, required credentials, primary outputs, reporting checklist, and honesty rules.
- [ ] The discovery support skill documents candidate preview rules and forbids production-ready Shootable Angle language before Gemini evidence exists.
- [ ] The evidence support skill documents evidence-only rerun behavior, expected outputs, evidence statuses, Manual Review Flags, and Claim Safety Review reporting.
- [ ] README and glossary language describe the normal workflow as a Daily Evidence Run using a Daily Top-5 Selection.
- [ ] Current skills and high-level docs do not present weekly/default-batch/deep-run behavior as the normal operating path.
- [ ] Long brand voice and virality guidance is referenced from shared source documents rather than duplicated across skills.
- [ ] The discovery config example remains valid JSON.
- [ ] The automation prompt for scheduled runs triggers the primary Daily Evidence Run skill and requires final output paths, evidence statuses, top Shootable Angles, Claim Safety Review risks, Manual Review Flags, and missing/failed evidence.
- [ ] No runtime pipeline behavior changes are required unless a verification check reveals the docs no longer match the actual daily CLI behavior.

## Blocked By

None - can start immediately.
