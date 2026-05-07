# Batch Analysis Run

- Run timestamp: 2026-05-07T17:43:29Z
- Mode: daily
- Requested batch size: 1
- Status: selected_batch_preview_created
- Manifest: `run_manifest.json`

## Output Folders

- `reports`
- `data`
- `evidence`
- `logs`

## Final Outputs

- Top 5 Creative Production Report (markdown): `reports/2026-05-08/20260507T174329Z_daily/top5_creative_production_report_2026-05-08.md`
- Excel Planning Workbook (spreadsheet): `reports/2026-05-08/20260507T174329Z_daily/top5_angle_planning_sheet_2026-05-08.xlsx`

## Selection

- JSON: `data/selected_batch.json`
- Markdown: `reports/selected_batch.md`

## Evidence Bundles

- Index: `data/evidence_bundle_index.json`

## Internal Structured Data

- Structured JSON: `data/structured_batch_analysis.json`

## Telegram Delivery

- Delivery log: `logs/telegram_delivery.json`

## Cleanup And Refinement

- Cleanup log: `logs/evidence_artifact_cleanup.json`
- Refinement hooks: `data/refinement_hooks.json`

## Not Implemented Yet

Source video artifacts are only present when candidate metadata includes a downloadable video source.
