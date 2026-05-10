# Add One-Time Legacy Artifact Import

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Add a one-time import path that moves existing local run artifacts and any required legacy dashboard state into Supabase Postgres and Supabase Storage. This should be a migration aid, not ongoing SQLite runtime support.

The completed slice should make historical reports and artifacts available in the new dashboard after migration.

## Acceptance criteria

- [ ] Import existing run metadata from current artifact folders into Supabase Postgres.
- [ ] Upload existing large artifacts to Supabase Storage with stable object paths.
- [ ] Write artifact metadata rows with bucket, object path, size, checksum when available, created time, and run id.
- [ ] If legacy SQLite contains state that is not recoverable from artifacts, read it only as a one-time import source.
- [ ] The import is idempotent or safely upserts by stable keys.
- [ ] The import does not add SQLite runtime support to the new dashboard.
- [ ] Add tests with fixture artifacts and optional legacy SQLite fixture data.
- [ ] Document how to run the import during migration.

## Blocked by

- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
- `docs/issues/0081-add-supabase-storage-artifact-access.md`
