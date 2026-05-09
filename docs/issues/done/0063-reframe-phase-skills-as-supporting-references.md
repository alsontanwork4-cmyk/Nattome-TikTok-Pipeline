# Reframe Phase Skills As Supporting References

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Update the discovery and evidence-analysis phase skills so they are clearly supporting references for debugging and reruns, not normal user-facing alternatives to the Daily Evidence Run.

Discovery should own scraper configuration, candidate handoff outputs, and candidate preview rules. Evidence analysis should own evidence-only rerun behavior, expected outputs, evidence statuses, Manual Review Flags, and Claim Safety Review reporting.

## Acceptance criteria

- [x] `nattome-tiktok-candidate-discovery` is marked or described as a supporting reference, not a normal entry point.
- [x] `nattome-evidence-insight-analysis` is marked or described as a supporting reference, not a normal entry point.
- [x] Both phase skills point normal users back to `nattome-viral-intelligence-run`.
- [x] The discovery support skill documents the daily top-5 handoff output.
- [x] The discovery support skill labels pre-Gemini reads as candidate previews or metadata inferences.
- [x] The discovery support skill forbids production-ready Shootable Angle language before Gemini evidence exists.
- [x] The evidence support skill documents `--mode daily` reruns on an existing daily candidate JSON.
- [x] The evidence support skill preserves Gemini evidence statuses exactly.
- [x] The evidence support skill requires surfacing Manual Review Flags and Claim Safety Review findings.
- [x] Long brand and virality prose is referenced from shared files rather than duplicated in phase skills.

## Blocked by

- `docs/issues/0062-make-daily-evidence-run-the-primary-skill.md`

## Completion notes

- Added contract coverage for phase skills as support-only references.
- Tightened discovery language to use Daily Top-5 Selection consistently.
- Made pre-Gemini prohibitions explicit for Shootable Angle, Nattome Priority Score, and production-ready language.
- Updated evidence-only rerun guidance to use `data/daily_runs/<run_id>/daily_selection_top5.json`.
