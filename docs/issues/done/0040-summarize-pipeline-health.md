# Summarize Pipeline Health

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build a Pipeline Health summarizer that converts indexed run phases, output presence, logs, and known artifact states into marketer-readable operational status. Pipeline Health must stay visually and conceptually separate from Scrape Quality.

The marketer should see plain-language impact first, with technical details available on expand for debugging.

## Acceptance criteria

- [ ] Pipeline Health summarizes Apify scrape status, raw candidate file status, selected batch status, source video availability, Gemini evidence status, report generation, Excel generation, Telegram delivery, and phase errors where available.
- [ ] Health summaries use severity levels: info, warning, error, and blocked.
- [ ] Plain-language impact summaries are generated for completed, partial, warning, error, and blocked phases.
- [ ] Technical drill-down includes phase, status, log path, raw JSON or exception text when available, file path, and timestamp.
- [ ] Pipeline Health does not affect Scrape Quality Score.
- [ ] Tests cover representative completed, partial, failed, and blocked run artifacts.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
