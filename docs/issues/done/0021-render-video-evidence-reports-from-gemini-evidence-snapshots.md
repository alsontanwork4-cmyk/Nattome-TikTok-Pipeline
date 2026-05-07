# Render Video Evidence Reports From Gemini Evidence Snapshots

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Update Video Evidence Report, Evidence Quality Score, Baseline Audio Analysis, and Claim Safety Review generation to consume Evidence Bundle snapshots populated by Gemini evidence. These modules should use structured evidence states rather than manually reading raw artifact files.

This slice keeps Evidence-First Analysis intact while moving report and review generation onto the new snapshot interface.

## Acceptance Criteria

- [ ] Video Evidence Reports render from Evidence Bundle snapshots.
- [ ] Evidence Quality Score evaluates Gemini-derived visual, text, spoken, audio, hook, and claim evidence.
- [ ] Baseline Audio Analysis consumes Gemini evidence rather than local transcription artifacts.
- [ ] Claim Safety Review consumes Gemini claim evidence, visible text, and spoken content.
- [ ] Missing Gemini evidence results in explicit uncertainty or manual review states, not fabricated claims.
- [ ] Reports are written under the two-layer Run Folder layout.
- [ ] Tests cover complete, partial, and missing Gemini evidence snapshots.
- [ ] Tests verify that report and review modules do not need raw artifact path knowledge.

## Blocked By

- `0020-add-gemini-2-5-flash-tool-stack-adapter.md`
