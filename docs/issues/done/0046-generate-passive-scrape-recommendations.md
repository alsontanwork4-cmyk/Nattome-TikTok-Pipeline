# Generate Passive Scrape Recommendations

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build passive recommendations that help marketers improve scrape quality based on Scrape Quality drivers and lightweight curation labels. Recommendations should explain their evidence and never mutate scrape settings automatically.

## Acceptance criteria

- [ ] Recommendations can be generated from low score drivers such as weak source input performance, low eligibility yield, stale videos, low relevance, low engagement, and duplicate/noise issues.
- [ ] Recommendations can use marketer labels and notes as supporting evidence.
- [ ] Recommendations link to supporting videos, runs, source inputs, labels, and config versions where available.
- [ ] Recommendations include lifecycle states: accepted, ignored, needs more data, and resolved.
- [ ] Marking a recommendation state does not change scrape settings.
- [ ] Underlying config changes can resolve stale recommendations.
- [ ] Tests prove recommendations are advisory and do not mutate settings or scores.
- [ ] Tests cover recommendation creation, evidence links, lifecycle state changes, and resolution.

## Blocked by

- `docs/issues/0039-compute-scrape-quality-score.md`
- `docs/issues/0042-browse-and-curate-raw-scraped-videos.md`
- `docs/issues/0043-manage-scrape-settings-with-version-history.md`
