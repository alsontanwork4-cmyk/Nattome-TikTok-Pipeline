# Add MVP Dashboard Exports

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Add simple MVP export features for marketer workflows. The dashboard should export filtered raw videos and run summaries to CSV, and approved patterns and Nattome POVs to Markdown. Existing final reports and Excel workbooks should remain linked rather than replaced.

## Acceptance criteria

- [ ] Filtered raw video results can be exported to CSV.
- [ ] Run summaries can be exported to CSV.
- [ ] Approved Patterns can be exported to Markdown.
- [ ] Nattome POVs can be exported to Markdown.
- [ ] Exports include enough metadata to preserve source links, run/config context, labels, and status where relevant.
- [ ] Existing Markdown reports and Excel workbooks remain linked as source deliverables.
- [ ] MVP does not include custom deck generation or a custom report builder.
- [ ] Tests cover CSV export shape, Markdown export shape, filtered export behavior, and empty export behavior.

## Blocked by

- `docs/issues/0042-browse-and-curate-raw-scraped-videos.md`
- `docs/issues/0045-run-history-trend-monitoring.md`
- `docs/issues/0047-build-candidate-and-approved-pattern-library.md`
- `docs/issues/0048-build-nattome-pov-library.md`
