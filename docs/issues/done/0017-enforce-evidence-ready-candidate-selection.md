# Enforce Evidence-Ready Candidate Selection

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Update the Minimum Eligibility Filter so Batch Analysis Runs exclude candidates without a downloadable video source by default. Preserve an explicit configuration override for metadata-only or debug selection previews, and make missing video source a separate exclusion reason.

This slice should keep candidate selection evidence-ready without changing unrelated ranking, scoring, or output behavior.

## Acceptance Criteria

- [ ] Candidates without a downloadable video source are excluded by default.
- [ ] Downloadability at selection time is checked by source field presence only.
- [ ] Missing downloadable video source is reported as a separate exclusion reason.
- [ ] An explicit configuration override allows metadata-only or debug selection previews.
- [ ] Existing candidate scoring and ranking behavior is preserved for eligible candidates.
- [ ] Focused tests cover default exclusion, override behavior, and the exclusion reason.
- [ ] Existing Batch Analysis Run tests still pass or are intentionally updated for the new eligibility rule.

## Blocked By

- None - can start immediately
