# Create Supabase Dashboard Data Contract

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Create the compact Supabase Postgres and Storage data contract for the new dashboard. The slice should define how the FastAPI app reads and writes run metadata, statuses, selected/raw videos, settings versions, manual runs, curation, and artifact metadata without introducing a generic repository-per-table layer.

The completed slice should give later route slices a testable Supabase boundary.

## Acceptance criteria

- [ ] Define Supabase Postgres table expectations for `runs`, `run_outputs`, `raw_videos`, `selected_videos`, `video_curation`, `scrape_settings_versions`, and `manual_runs`.
- [ ] Define artifact metadata fields for Supabase Storage bucket, object path, size, checksum when available, created time, and run id.
- [ ] Add a compact `dashboard/supabase_client.py` or equivalent boundary for Postgres and Storage access.
- [ ] Add focused query/write helpers only where immediately needed by upcoming slices.
- [ ] Provide fake or isolated Supabase clients for tests.
- [ ] Do not add SQLite runtime support, placeholder repositories, or repository-per-table abstractions.
- [ ] Add tests for the data contract and artifact metadata handling.

## Blocked by

- `docs/issues/0075-bootstrap-supabase-first-fastapi-shell.md`
