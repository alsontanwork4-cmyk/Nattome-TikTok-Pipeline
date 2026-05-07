# Build Pipeline Architecture Browser

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build a read-only Pipeline Architecture section that helps a new Nattome marketer understand the system without leaving the dashboard. It should expose architecture docs, tool decisions, PRDs, ADRs, phase/status map, file/output map, and data lineage.

## Acceptance criteria

- [ ] Pipeline Architecture lists indexed README, CONTEXT, PRDs, ADRs, and relevant skill documentation.
- [ ] Architecture docs are read-only in the dashboard.
- [ ] The page explains the high-level pipeline flow from scrape to score to select to analyze to report.
- [ ] The page shows the tool stack and key decisions, including Apify discovery/download and Gemini evidence-first analysis.
- [ ] The page shows a phase/status map using indexed run metadata where available.
- [ ] The page shows a file/output map linking raw scrapes, run folders, reports, workbooks, logs, and docs.
- [ ] The page shows data lineage from raw scrape through selected batch and final outputs where available.
- [ ] Tests cover docs indexing and architecture data view-model generation.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
