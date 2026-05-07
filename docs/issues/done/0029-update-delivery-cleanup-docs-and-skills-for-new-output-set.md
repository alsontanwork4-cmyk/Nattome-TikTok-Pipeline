# Update Delivery Cleanup Docs And Skills For New Output Set

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Update user-facing references and support paths so the pipeline consistently presents the new final output set.

Telegram delivery messaging, cleanup preservation rules, README documentation, Nattome skill instructions, and any user-facing workflow text should point users to the new Top 5 Creative Production Report and Excel planning workbook. Obsolete references to the Daily TikTok Brief, Cross-Video Pattern Summary Markdown, and CSV Spreadsheet Summary should be removed or reframed as internal/historical where appropriate.

## Acceptance Criteria

- [ ] Telegram delivery messaging points to the new Top 5 Creative Production Report when delivery is enabled.
- [ ] Telegram delivery messaging points to the new Excel planning workbook when delivery is enabled.
- [ ] Telegram delivery messaging does not present the old Cross-Video Pattern Summary or CSV Spreadsheet Summary as final deliverables for new runs.
- [ ] Cleanup preservation rules preserve `outputs/reports/YYYY-MM-DD/top5_creative_production_report_YYYY-MM-DD.md`.
- [ ] Cleanup preservation rules preserve `outputs/reports/YYYY-MM-DD/top5_angle_planning_sheet_YYYY-MM-DD.xlsx`.
- [ ] Cleanup behavior does not require migrating or deleting historical run outputs.
- [ ] README output descriptions match the new final output shape.
- [ ] Nattome batch analysis skill instructions match the new final output shape.
- [ ] Daily discovery skill references are updated if they still point users toward the removed final daily brief workflow.
- [ ] User-facing documentation no longer describes the old three-output shape as the current final deliverable.
- [ ] Tests cover Telegram message output path changes where existing Telegram tests apply.
- [ ] Tests cover cleanup preservation for the new final report and workbook.

## Blocked By

- `docs/issues/0028-replace-final-batch-output-registration.md`
