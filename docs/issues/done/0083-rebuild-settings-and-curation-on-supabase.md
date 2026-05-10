# Rebuild Settings And Curation On Supabase

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Rebuild scrape settings and video curation flows on Supabase. The dashboard should let authenticated users view settings, save a new settings version, roll back settings, and save curation labels/notes with Supabase Auth audit identity.

The completed slice should preserve the operational value of settings and curation while removing the SQLite runtime dependency.

## Acceptance criteria

- [ ] Implement authenticated `GET /settings`.
- [ ] Implement authenticated `POST /settings`.
- [ ] Implement authenticated `POST /settings/{version}/rollback`.
- [ ] Implement authenticated `POST /videos/{video_id}/curation`.
- [ ] Validate form data server-side and show clear errors.
- [ ] Settings changes are versioned and rollbackable in Supabase Postgres.
- [ ] Curation labels and notes persist in Supabase Postgres.
- [ ] Audit fields use the authenticated Supabase user identity.
- [ ] Settings and curation pages follow the legacy dashboard visual language and reused theme assets.
- [ ] Add tests for settings view, save, rollback, validation errors, curation persistence, and unauthenticated rejection.

## Blocked by

- `docs/issues/0077-add-supabase-auth-gate.md`
- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
- `docs/issues/0079-build-runs-list-and-run-detail-from-supabase.md`
