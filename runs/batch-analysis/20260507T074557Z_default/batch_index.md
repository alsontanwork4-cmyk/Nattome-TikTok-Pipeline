# Batch Analysis Run

- Run timestamp: 2026-05-07T07:45:57Z
- Mode: default
- Requested batch size: 10
- Status: selected_batch_preview_created
- Manifest: `run_manifest.json`

## Output Folders

- `reports`
- `data`
- `evidence`
- `logs`

## Selection

- JSON: `data/selected_batch.json`
- Markdown: `reports/selected_batch.md`

## Evidence Bundles

- Index: `data/evidence_bundle_index.json`

## Cross-Video Pattern Summary

- Markdown: `reports/cross_video_pattern_summary.md`
- JSON: `data/cross_video_pattern_summary.json`

## Structured Outputs

- Structured JSON: `data/structured_batch_analysis.json`
- Spreadsheet summary: `data/spreadsheet_summary.csv`

## Telegram Delivery

- Delivery log: `logs/telegram_delivery.json`

## Cleanup And Refinement

- Cleanup log: `logs/evidence_artifact_cleanup.json`
- Refinement hooks: `data/refinement_hooks.json`

## Not Implemented Yet

Source video artifacts are only present when candidate metadata includes a downloadable video source.
