# Index Pipeline Artifacts Into SQLite

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build the artifact indexing path that reads existing Nattome TikTok Content Discovery Pipeline artifacts and normalizes them into dashboard SQLite records. The index should preserve existing raw scrapes, Batch Analysis Runs, run manifests, selected batches, final reports, Excel workbooks, logs, PRDs, ADRs, and domain docs as source artifacts while making them searchable and queryable.

Raw scraped videos should become the primary content records. Selected and analyzed state should be represented as status on those raw video records.

## Acceptance criteria

- [ ] Raw scrape JSON files are indexed as run/source records plus raw video records.
- [ ] Selected batch JSON files are indexed and linked back to raw video records.
- [ ] Batch Analysis Run manifests, metadata, logs, reports, and output links are indexed.
- [ ] Raw video records include TikTok URL, author, caption, hashtags, source input where available, engagement stats, created date, downloadability, run ID, and config version where available.
- [ ] Selected/analyzed status is represented on raw video records without hiding unselected videos.
- [ ] PRDs, ADRs, README, CONTEXT, and relevant skill docs are indexed as read-only documentation records.
- [ ] Reindexing can rebuild artifact-derived records without deleting dashboard-owned labels, notes, config versions, approved patterns, or POV edits.
- [ ] Tests cover indexing representative raw scrape, selected batch, run manifest, output link, and docs fixtures.

## Blocked by

- `docs/issues/0037-bootstrap-local-dashboard-shell.md`
