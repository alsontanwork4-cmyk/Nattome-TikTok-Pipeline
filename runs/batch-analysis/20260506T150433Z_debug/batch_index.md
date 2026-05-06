# Batch Analysis Run

- Run timestamp: 2026-05-06T15:04:33Z
- Mode: debug
- Requested batch size: 1
- Status: selected_batch_preview_created

## Output Folders

- `batch_outputs/markdown`
- `batch_outputs/json`
- `batch_outputs/spreadsheets`
- `evidence_bundles`
- `logs`

## Selection

- JSON: `batch_outputs/json/selected_batch.json`
- Markdown: `batch_outputs/markdown/selected_batch.md`

## Evidence Bundles

- Index: `evidence_bundles/index.json`

## Cross-Video Pattern Summary

- Markdown: `batch_outputs/markdown/cross_video_pattern_summary.md`
- JSON: `batch_outputs/json/cross_video_pattern_summary.json`

## Structured Outputs

- Structured JSON: `batch_outputs/json/structured_batch_analysis.json`
- Spreadsheet summary: `batch_outputs/spreadsheets/spreadsheet_summary.csv`

## Telegram Delivery

- Delivery log: `logs/telegram_delivery.json`

## Cleanup And Refinement

- Cleanup log: `logs/evidence_artifact_cleanup.json`
- Refinement hooks: `batch_outputs/json/refinement_hooks.json`

## Not Implemented Yet

Source video artifacts are only present when candidate metadata includes a downloadable video source.
