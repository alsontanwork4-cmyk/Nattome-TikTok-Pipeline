# Remove Cleanup Fallbacks For Retired Outputs

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Make cleanup preservation rely on manifest-registered final outputs instead of the old fallback set containing Cross-Video Markdown and CSV files.

Cleanup should preserve the current final marketer-facing deliverables, which are the Top 5 Creative Production Report and Excel planning workbook under `outputs/reports/YYYY-MM-DD/`. It should not require retired files to decide whether durable outputs exist.

## Acceptance Criteria

- [x] `durable_outputs_exist` checks manifest `outputs.final_outputs` and `outputs.output_root`.
- [x] The fallback requirement for `reports/cross_video_pattern_summary.md` is deleted.
- [x] The fallback requirement for `data/spreadsheet_summary.csv` is deleted.
- [x] Cleanup tests cover preserving `top5_creative_production_report_YYYY-MM-DD.md`.
- [x] Cleanup tests cover preserving `top5_angle_planning_sheet_YYYY-MM-DD.xlsx`.
- [x] Cleanup tests no longer create retired output files as durable outputs.
- [x] Historical run folders are not migrated or modified.

## Blocked By

- `docs/issues/0030-remove-cross-video-markdown-report-output.md`
- `docs/issues/0031-remove-csv-spreadsheet-summary-output.md`
