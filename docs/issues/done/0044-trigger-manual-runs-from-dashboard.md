# Trigger Manual Runs From Dashboard

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Add manual run controls so marketers can trigger a fast scrape/discovery run or a slower full pipeline run from the dashboard. Manual runs must be labeled separately from scheduled runs, record provenance, show progress/status, and avoid overwriting existing artifacts.

## Acceptance criteria

- [ ] Dashboard exposes `Run scrape now` and `Run full pipeline` actions.
- [ ] Run scrape now launches the scrape/discovery path using the active production config.
- [ ] Run full pipeline launches scrape, selection, evidence analysis, final reports, workbook generation, and delivery behavior using the active production config.
- [ ] The UI shows estimated runtime and expected outputs before launch.
- [ ] Manual runs record run type, config version, triggered_by, timestamp, status, and output paths where available.
- [ ] Manual runs are distinct from scheduled runs in indexed records.
- [ ] Manual runs never overwrite previous scheduled or manual artifacts.
- [ ] Progress and final status are visible in the dashboard.
- [ ] Completed manual runs are indexed automatically.
- [ ] Tests cover scrape-only run record creation, full-pipeline run record creation, status handling, and no-overwrite behavior using faked command execution where appropriate.

## Blocked by

- `docs/issues/0043-manage-scrape-settings-with-version-history.md`
