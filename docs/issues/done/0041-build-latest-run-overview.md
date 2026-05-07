# Build Latest Run Overview

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build the first usable marketer-facing dashboard screen: Latest Run Overview. It should show the latest indexed run, Scrape Quality Score, Pipeline Health, current config version, next scheduled run if known, top raw scraped videos, quality drivers, and primary dashboard actions.

This screen should make it immediately clear whether the latest scrape was strong, usable, or needs attention, and whether the pipeline processed it cleanly.

## Acceptance criteria

- [ ] Overview shows Scrape Quality Score with band and top quality drivers.
- [ ] Overview shows Pipeline Health separately from Scrape Quality.
- [ ] Overview shows latest run timestamp and run type when available.
- [ ] Overview shows current config version and next scheduled run information when available.
- [ ] Overview shows a preview of top raw scraped videos with metadata and outbound TikTok links.
- [ ] Overview includes primary actions for Run scrape now, Run full pipeline, Edit scrape settings, View run history, and Browse content library.
- [ ] Empty and missing-artifact states are understandable to a marketer.
- [ ] Tests or UI smoke coverage verify Overview renders with no runs, with a strong run, and with a needs-attention run.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
- `docs/issues/0039-compute-scrape-quality-score.md`
- `docs/issues/0040-summarize-pipeline-health.md`
