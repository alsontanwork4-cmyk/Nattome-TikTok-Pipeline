# Remove Cross-Video Markdown Report Output

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Remove the retired `cross_video_pattern_summary.md` visible output path.

The Cross-Video Pattern Summary may continue to exist as internal structured JSON because it still feeds structured batch analysis, Telegram messaging, refinement hooks, and Top 5 report/workbook support paths. This issue only removes the obsolete Markdown report output and the old interface option that can still write it.

## Acceptance Criteria

- [x] `write_cross_video_pattern_summary` always writes `data/cross_video_pattern_summary.json`.
- [x] `write_cross_video_pattern_summary` no longer accepts a `write_markdown` option.
- [x] No new run or direct module call can write `reports/cross_video_pattern_summary.md`.
- [x] Batch index and manifest behavior still list only the Top 5 Creative Production Report and Excel planning workbook as final outputs.
- [x] Tests that asserted `reports/cross_video_pattern_summary.md` exists are removed or rewritten around internal JSON.
- [x] Tests still verify `top_priority_shootable_angles`, pattern comparison data, and recommendation data in `cross_video_pattern_summary.json`.

## Blocked By

None - can start immediately
