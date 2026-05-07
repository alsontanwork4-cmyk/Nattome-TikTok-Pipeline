# Remove Obsolete Spreadsheet Summary Status Surface

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Remove the old `spreadsheet_summary` implementation status from run metadata so completed runs no longer advertise a retired CSV output.

After this issue, `structured_json_output` remains the internal structured data status, and the Excel workbook is represented through final output registration rather than the old CSV status key.

## Acceptance Criteria

- [x] `build_metadata` no longer accepts `has_spreadsheet_summary`.
- [x] `run_metadata.json` no longer contains `implementation_status.spreadsheet_summary`.
- [x] `implementation_status.structured_json_output` remains present and accurate.
- [x] Tests no longer assert `spreadsheet_summary` is implemented.
- [x] Any remaining `spreadsheet_summary` references in `batch_analysis` are gone except historical PRD or completed-issue text.

## Blocked By

- `docs/issues/0031-remove-csv-spreadsheet-summary-output.md`
