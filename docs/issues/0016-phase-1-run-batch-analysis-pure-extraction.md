# Phase 1 Run Batch Analysis Pure Extraction

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/phase-1-run-batch-analysis-pure-extraction-prd.md`

## What To Build

Compact the Batch Analysis Run implementation through pure extraction. Preserve the current CLI Interface exactly while moving configuration, candidate handling, and Batch Analysis Run orchestration into domain-shaped Modules.

This issue must not change output schemas, command flags, Run Folder layout, Evidence Bundle behavior, Tool Stack behavior, Telegram Delivery behavior, or cleanup behavior.

## Acceptance Criteria

- [ ] The Batch Analysis Run command still accepts the same flags.
- [ ] The Batch Analysis Run command still prints the same success message.
- [ ] Invalid inputs still return the same failure behavior.
- [ ] The command-line script is reduced to a thin CLI Adapter.
- [ ] Runtime configuration loading and merging live in a dedicated Module.
- [ ] Candidate loading, filtering, scoring, ranking, and normalization live in a dedicated Module.
- [ ] Batch Analysis Run orchestration is callable from an importable Module.
- [ ] Existing tests pass without expected output changes.
- [ ] Known behavior issues discovered during extraction are documented but not fixed as part of this issue.

## Blocked By

- None
