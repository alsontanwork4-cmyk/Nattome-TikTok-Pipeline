# Generate Two-Sheet Excel Planning Workbook

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Add the new Excel production planning workbook output for completed runs.

The workbook should be written as `outputs/reports/YYYY-MM-DD/top5_angle_planning_sheet_YYYY-MM-DD.xlsx` and contain exactly two sheets: `Angles` and `Source Videos`. The `Angles` sheet should have one row per Nattome angle, while the `Source Videos` sheet should have one row per selected source video. The workbook should preserve planning and scoring fields such as priority score and evidence quality, while keeping full scripts in the Markdown report only.

## Acceptance Criteria

- [ ] A completed run can write `outputs/reports/YYYY-MM-DD/top5_angle_planning_sheet_YYYY-MM-DD.xlsx`.
- [ ] The workbook contains exactly two sheets named `Angles` and `Source Videos`.
- [ ] The `Angles` sheet has one row per Nattome angle.
- [ ] For a top-five run with three angles per video, the `Angles` sheet has 15 data rows.
- [ ] The `Source Videos` sheet has one row per selected source video.
- [ ] For a top-five run, the `Source Videos` sheet has 5 data rows.
- [ ] The `Angles` sheet marks which angle is the Recommended Shoot.
- [ ] The `Angles` sheet marks exactly one Recommended Shoot per source video.
- [ ] The workbook includes priority score fields where available.
- [ ] The workbook includes evidence quality fields where available.
- [ ] The workbook includes source link, creator, engagement stats, concept, hook, format, and why-it-works fields where available.
- [ ] Full scripts are not written into workbook cells.
- [ ] The workbook writer has a narrow testable interface.
- [ ] Tests verify sheet names, row counts, recommended-shoot markers, scoring fields, and absence of full scripts.

## Blocked By

- `docs/issues/0025-build-top-5-creative-report-tracer.md`
