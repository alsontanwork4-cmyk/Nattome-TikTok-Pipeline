# Migrate Full Batch Analysis Run To The New Architecture

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Migrate the full Batch Analysis Run CLI path to use the new two-layer Run Folder layout, Run Manifest, Evidence Bundle snapshots, Gemini Tool Stack Adapter seam, local Shootable Angle generation, and manifest-registered Batch Output Set.

This slice proves the architecture works end-to-end for new runs and removes the old nested writer path from the normal workflow.

## Acceptance Criteria

- [ ] The Batch Analysis Run CLI executes end-to-end using the new architecture.
- [ ] New runs use the two-layer Run Folder layout exclusively.
- [ ] New runs write `run_manifest.json` and generate `batch_index.md` from it.
- [ ] New runs use Evidence Bundle snapshots for downstream report, review, summary, and output generation.
- [ ] New runs use the Gemini Tool Stack Adapter seam for evidence extraction.
- [ ] New runs generate local evidence-backed Shootable Angles.
- [ ] New runs produce Video Evidence Reports, Cross-Video Pattern Summary, Structured JSON Output, Spreadsheet Summary Output, Telegram Delivery logs, cleanup logs, and refinement hooks when configured.
- [ ] New runs do not write the legacy nested batch output or evidence bundle layout.
- [ ] End-to-end regression tests cover success, missing Gemini evidence, and partial run failure behavior.
- [ ] Existing archived historical runs are not migrated or modified.

## Blocked By

- `0017-enforce-evidence-ready-candidate-selection.md`
- `0018-create-two-layer-run-folder-and-run-manifest-skeleton.md`
- `0019-write-evidence-bundle-snapshots-in-two-layer-layout.md`
- `0020-add-gemini-2-5-flash-tool-stack-adapter.md`
- `0021-render-video-evidence-reports-from-gemini-evidence-snapshots.md`
- `0022-generate-evidence-backed-shootable-angles-locally.md`
- `0023-produce-batch-outputs-and-delivery-logs-from-the-manifest.md`
