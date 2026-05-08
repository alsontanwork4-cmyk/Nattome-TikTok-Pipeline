# Reframe Phase Skills As Supporting References

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Update the discovery and evidence-analysis phase skills so they are clearly supporting references for debugging and reruns, not normal user-facing alternatives to the Daily Evidence Run.

Discovery should own scraper configuration, candidate handoff outputs, and candidate preview rules. Evidence analysis should own evidence-only rerun behavior, expected outputs, evidence statuses, Manual Review Flags, and Claim Safety Review reporting.

## Acceptance criteria

- [ ] `nattome-tiktok-candidate-discovery` is marked or described as a supporting reference, not a normal entry point.
- [ ] `nattome-evidence-insight-analysis` is marked or described as a supporting reference, not a normal entry point.
- [ ] Both phase skills point normal users back to `nattome-viral-intelligence-run`.
- [ ] The discovery support skill documents the daily top-5 handoff output.
- [ ] The discovery support skill labels pre-Gemini reads as candidate previews or metadata inferences.
- [ ] The discovery support skill forbids production-ready Shootable Angle language before Gemini evidence exists.
- [ ] The evidence support skill documents `--mode daily` reruns on an existing daily candidate JSON.
- [ ] The evidence support skill preserves Gemini evidence statuses exactly.
- [ ] The evidence support skill requires surfacing Manual Review Flags and Claim Safety Review findings.
- [ ] Long brand and virality prose is referenced from shared files rather than duplicated in phase skills.

## Blocked by

- `docs/issues/0062-make-daily-evidence-run-the-primary-skill.md`
