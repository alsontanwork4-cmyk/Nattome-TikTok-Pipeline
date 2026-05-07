# Replace Final Batch Output Registration

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Switch new completed runs to the new final marketer-facing Batch Output Set.

After this slice, the final visible outputs for a completed run should be the Top 5 Creative Production Report and the Excel planning workbook in `outputs/reports/YYYY-MM-DD/`. The old Daily TikTok Brief, Cross-Video Pattern Summary Markdown, and CSV Spreadsheet Summary should no longer be written or registered as final visible outputs for new runs.

Run manifest output registration, batch index rendering, and any output path summaries should point to the new report and workbook. Internal structured data may continue to exist where needed, but it should not recreate the old scattered final deliverables.

## Acceptance Criteria

- [ ] New completed runs register the Top 5 Creative Production Report as a final visible Markdown output.
- [ ] New completed runs register the Excel planning workbook as a final visible spreadsheet output.
- [ ] New completed runs no longer write `daily_brief_YYYY-MM-DD.md` as a final visible output.
- [ ] New completed runs no longer write `cross_video_pattern_summary.md` as a final visible Markdown output.
- [ ] New completed runs no longer write `spreadsheet_summary.csv` as a final visible output.
- [ ] The run manifest references the new report and workbook paths where final outputs are listed.
- [ ] The batch index references the new report and workbook instead of the old Cross-Video Pattern Summary and CSV Spreadsheet Summary.
- [ ] Existing internal structured JSON can still be generated where required by downstream automation or tests.
- [ ] Historical run folders are not migrated or modified.
- [ ] Tests verify the new final output pair is registered.
- [ ] Tests verify old final visible output paths are not registered for new runs.
- [ ] CLI-scale regression coverage verifies a completed run produces the new final output pair.
- [ ] CLI-scale regression coverage verifies old final visible Markdown and CSV files are not produced for new runs.

## Blocked By

- `docs/issues/0025-build-top-5-creative-report-tracer.md`
- `docs/issues/0026-add-recommended-shoot-timed-scripts.md`
- `docs/issues/0027-generate-two-sheet-excel-planning-workbook.md`
