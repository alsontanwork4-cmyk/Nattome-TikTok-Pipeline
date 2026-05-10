# Build Runs List And Run Detail From Supabase

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Build the first real authenticated dashboard data view from Supabase: a run history list and run detail page. The page should make pipeline status understandable from the browser without requiring SSH.

The completed slice should implement `GET /runs` and `GET /runs/{run_id}` using Supabase metadata and the legacy visual theme.

## Acceptance criteria

- [ ] Implement `GET /runs` for newest-first run history.
- [ ] Implement `GET /runs/{run_id}` for selected run detail.
- [ ] Show start time, end time, duration, run type, status, output metadata, and error summary where available.
- [ ] Display queued, running, succeeded, failed, and canceled states if canceled is supported.
- [ ] Failed runs expose a concise error summary without rendering secrets or full environment dumps.
- [ ] The runs pages follow the legacy dashboard visual language and reused theme assets.
- [ ] Add tests for populated runs, empty runs, missing run id, and each supported status display.
- [ ] Do not depend on the old dashboard request handler or SQLite store.

## Blocked by

- `docs/issues/0077-add-supabase-auth-gate.md`
- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
