# Add Global Search And Facets

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Add global keyword search and faceted filtering across dashboard records so marketers can find raw videos, runs, labels, notes, patterns, POVs, reports, and architecture docs from one place.

## Acceptance criteria

- [ ] Global keyword search covers raw videos, runs, labels, notes, Candidate Patterns, Approved Patterns, Nattome POVs, reports, and architecture docs.
- [ ] Search results show the record type and useful context.
- [ ] Facets include run date, run type, config version, source input, video status, label, score band, relevance band, engagement band, freshness, author, hashtag/topic, pattern, POV, market, campaign, product, and pipeline phase/status where available.
- [ ] Facets can be combined with keyword search.
- [ ] Search gracefully handles empty results.
- [ ] Tests cover keyword search, facet filtering, combined filters, and result typing across representative records.

## Blocked by

- `docs/issues/0042-browse-and-curate-raw-scraped-videos.md`
- `docs/issues/0045-run-history-trend-monitoring.md`
- `docs/issues/0047-build-candidate-and-approved-pattern-library.md`
- `docs/issues/0048-build-nattome-pov-library.md`
- `docs/issues/0049-build-pipeline-architecture-browser.md`
