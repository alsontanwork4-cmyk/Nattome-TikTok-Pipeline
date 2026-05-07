# Remove User-Facing Daily Brief Final Output References

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Update README and skill workflow text so users are not directed toward `daily_brief_YYYY-MM-DD.md` as part of the current final production report style.

Daily Discovery can remain a discovery or handoff workflow if useful, but the current production deliverables should be the Top 5 Creative Production Report and Excel planning workbook.

## Acceptance Criteria

- [x] README describes final production deliverables as the Top 5 Creative Production Report plus Excel planning workbook.
- [x] Daily Discovery references are reframed as discovery or handoff inputs, not the current production report.
- [x] `skills/nattome-daily-discovery` no longer instructs users to treat `daily_brief_YYYY-MM-DD.md` as the final production report.
- [x] `skills/nattome-batch-analysis` still points to `top5_creative_production_report_YYYY-MM-DD.md` and `top5_angle_planning_sheet_YYYY-MM-DD.xlsx`.
- [x] Skill eval or workflow text is updated if it still expects the old Daily Brief as the primary output.
- [x] No behavior code changes are required for this issue unless tests cover documentation or skill text.

## Blocked By

None - can start immediately
