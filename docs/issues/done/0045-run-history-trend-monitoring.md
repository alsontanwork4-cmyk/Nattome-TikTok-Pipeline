# Run History Trend Monitoring

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build Run History as the marketer's feedback loop for scrape quality and config changes. The page should optimize for trend monitoring first, with drill-down audit/debug detail available for each run.

## Acceptance criteria

- [ ] Run History lists scheduled and manual runs.
- [ ] Each run row shows timestamp, run type, config version, Scrape Quality Score, raw candidates, eligible candidates, selected count, average Nattome relevance, average engagement, freshness score, duplicate/noise score, Pipeline Health, top issue, and output links where available.
- [ ] Trend views show score, candidate volume, eligibility yield, relevance, engagement, and config version overlays over time.
- [ ] Clicking a run opens drill-down detail with raw content, selected content, quality drivers, pipeline phases, logs, and linked outputs.
- [ ] Existing Markdown reports and Excel workbooks remain linked rather than replaced.
- [ ] Empty and partial-history states are understandable.
- [ ] Tests cover run list rendering data, trend data construction, config overlay data, and run drill-down data.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
- `docs/issues/0039-compute-scrape-quality-score.md`
- `docs/issues/0040-summarize-pipeline-health.md`
- `docs/issues/0043-manage-scrape-settings-with-version-history.md`
- `docs/issues/0044-trigger-manual-runs-from-dashboard.md`
