# Rebuild Reports And CSV Exports From Supabase

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Rebuild report viewing and CSV export routes from Supabase-backed metadata and artifact access. The slice should let an authenticated user inspect reports and download raw-video or run-summary CSVs without the old request handler or SQLite store.

The completed slice should preserve the current dashboard's reporting/export utility while using the new resource-style routes.

## Acceptance criteria

- [ ] Implement authenticated `GET /reports`.
- [ ] Implement authenticated `GET /reports/{run_id}`.
- [ ] Render report Markdown through the Jinja page pattern.
- [ ] Missing report artifacts show a clear empty state.
- [ ] Implement `GET /exports/raw-videos.csv` from Supabase data.
- [ ] Implement `GET /exports/run-summaries.csv` from Supabase data.
- [ ] Download responses set correct content type and filename.
- [ ] The report and export pages follow the legacy dashboard visual language and reused theme assets.
- [ ] Add tests for report present, report missing, both CSV downloads, and unauthenticated rejection.

## Blocked by

- `docs/issues/0079-build-runs-list-and-run-detail-from-supabase.md`
- `docs/issues/0081-add-supabase-storage-artifact-access.md`
