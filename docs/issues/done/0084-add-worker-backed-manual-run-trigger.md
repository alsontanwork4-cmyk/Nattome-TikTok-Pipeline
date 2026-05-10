# Add Worker-Backed Manual Run Trigger

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Add the authenticated manual run trigger and worker status contract. FastAPI should create a queued manual run in Supabase and return quickly; a separate Python worker should claim queued work, enforce the active-run guard, update status, and hand off artifact upload to Supabase Storage.

The completed slice should make the hosted dashboard a real control surface without running long pipeline work inside the web request.

## Acceptance criteria

- [ ] Implement authenticated `POST /runs` to request a full pipeline run.
- [ ] Record trigger user, trigger time, run type, initial status, and expected output metadata in Supabase Postgres.
- [ ] Prevent duplicate active full-pipeline runs using the Supabase-backed active-run guard.
- [ ] Add a compact worker claim/status contract for queued, running, succeeded, failed, and canceled if supported.
- [ ] Long-running execution does not block the FastAPI request.
- [ ] Worker failures update visible status and a concise error summary without secrets.
- [ ] The trigger UI follows the legacy dashboard visual language and reused theme assets.
- [ ] Add tests for unauthenticated rejection, successful queueing, duplicate active run prevention, worker claim, and failure status.

## Blocked by

- `docs/issues/0077-add-supabase-auth-gate.md`
- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
- `docs/issues/0079-build-runs-list-and-run-detail-from-supabase.md`
- `docs/issues/0081-add-supabase-storage-artifact-access.md`
