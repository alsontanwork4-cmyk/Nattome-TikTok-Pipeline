# Remove CSV Spreadsheet Summary Output

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Delete the retired `spreadsheet_summary.csv` output branch.

Structured JSON remains the internal machine-readable output. The two-sheet Excel workbook remains the only spreadsheet deliverable for the current marketer-facing Batch Output Set.

## Acceptance Criteria

- [x] The structured output writer no longer accepts a `write_spreadsheet` option.
- [x] No code path writes `data/spreadsheet_summary.csv`.
- [x] The old CSV row-building and `csv.DictWriter` code is deleted.
- [x] The structured output writer returns only `structured_json_path`, status, and row/count metadata needed by callers.
- [x] Existing workbook tests continue to prove `top5_angle_planning_sheet_YYYY-MM-DD.xlsx` is the spreadsheet output.
- [x] Full CLI and two-layer regression tests assert `data/spreadsheet_summary.csv` does not exist for new completed runs.

## Blocked By

None - can start immediately
