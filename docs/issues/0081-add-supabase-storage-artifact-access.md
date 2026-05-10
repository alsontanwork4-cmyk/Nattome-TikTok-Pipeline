# Add Supabase Storage Artifact Access

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Add authenticated artifact access for files stored in Supabase Storage. The dashboard should serve or redirect to signed artifact downloads from metadata rows rather than reading VPS-local dashboard files.

The completed slice should make reports, workbooks, videos, raw JSON, evidence snapshots, and Gemini responses addressable through the new artifact route.

## Acceptance criteria

- [ ] Implement authenticated `GET /artifacts/{artifact_id}`.
- [ ] Resolve artifact metadata from Supabase Postgres.
- [ ] Generate a signed Supabase Storage URL or proxy the object through FastAPI.
- [ ] Return clear missing/unauthorized states when the artifact metadata or object is unavailable.
- [ ] Do not expose service-role secrets, bucket internals beyond the chosen public route, or raw environment values.
- [ ] Add tests for successful artifact access, missing metadata, missing object, and unauthorized access.
- [ ] Artifact links shown in pages follow the legacy dashboard visual language.

## Blocked by

- `docs/issues/0077-add-supabase-auth-gate.md`
- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
- `docs/issues/0079-build-runs-list-and-run-detail-from-supabase.md`
