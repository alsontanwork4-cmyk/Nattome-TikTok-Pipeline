# Build Overview From Supabase Runs

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Build the FastAPI dashboard overview at `GET /` from Supabase run metadata. The overview should show the latest run state, high-signal operational summary, and an empty state when no run data exists.

The completed slice should make the first screen useful while preserving the legacy dashboard look and feel.

## Acceptance criteria

- [ ] Implement authenticated `GET /`.
- [ ] Display latest run status, run timing, selected video counts, output availability, and top operational issue where available.
- [ ] Link from the overview to the relevant `/runs/{run_id}` and report/artifact routes.
- [ ] Display a clear empty state when Supabase has no run data.
- [ ] The overview follows the legacy dashboard visual language and reused theme assets.
- [ ] Add tests for populated and empty overview states.
- [ ] Do not depend on the old dashboard request handler or SQLite store.

## Blocked by

- `docs/issues/0077-add-supabase-auth-gate.md`
- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
- `docs/issues/0079-build-runs-list-and-run-detail-from-supabase.md`
