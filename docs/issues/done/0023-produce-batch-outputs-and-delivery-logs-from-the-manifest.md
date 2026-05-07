# Produce Batch Outputs And Delivery Logs From The Manifest

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Update Cross-Video Pattern Summary, Structured JSON Output, Spreadsheet Summary Output, Telegram Delivery logs, cleanup logs, and refinement hooks so they use the two-layer Run Folder layout and register their outputs in the Run Manifest.

This slice makes the Batch Output Set and operational logs consistent with the new manifest-driven architecture.

## Acceptance Criteria

- [ ] Cross-Video Pattern Summary is written under the two-layer layout.
- [ ] Structured JSON Output is written under the two-layer layout.
- [ ] Spreadsheet Summary Output is written under the two-layer layout.
- [ ] Telegram Delivery logs are written under the two-layer layout.
- [ ] Cleanup logs are written under the two-layer layout.
- [ ] Refinement hooks are written under the two-layer layout.
- [ ] All batch outputs and logs are registered in the Run Manifest.
- [ ] Cross-Video Pattern Summary consumes structured Shootable Angle data and does not invent angles while rendering.
- [ ] Spreadsheet Summary Output includes one scannable row per analyzed video.
- [ ] Tests verify output paths, manifest registrations, and no legacy nested output paths.

## Blocked By

- `0022-generate-evidence-backed-shootable-angles-locally.md`
