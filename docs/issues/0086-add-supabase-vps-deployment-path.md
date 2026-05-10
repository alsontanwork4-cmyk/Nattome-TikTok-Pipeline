# Add Supabase VPS Deployment Path

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Add the VPS deployment path for the Supabase-first FastAPI dashboard. The docs should cover the web app, the separate worker, reverse proxy, required environment variables, Supabase access, and backup expectations without relying on the old local server command.

The completed slice should give the owner enough concrete deployment material to run the dashboard on a VPS.

## Acceptance criteria

- [ ] Add FastAPI VPS deployment documentation.
- [ ] Provide a `systemd` service example for the FastAPI app.
- [ ] Provide a `systemd` service example for the worker.
- [ ] Provide an Nginx or Caddy reverse proxy example.
- [ ] Document required environment variables for Supabase URL/keys, Auth, Storage buckets, workspace, and production mode.
- [ ] Document the `uvicorn` production command.
- [ ] Document Supabase Postgres backup expectations.
- [ ] Document Supabase Storage backup/export expectations.
- [ ] Production docs do not instruct users to run the old dashboard server.

## Blocked by

- `docs/issues/0075-bootstrap-supabase-first-fastapi-shell.md`
- `docs/issues/0077-add-supabase-auth-gate.md`
- `docs/issues/0078-create-supabase-dashboard-data-contract.md`
- `docs/issues/0084-add-worker-backed-manual-run-trigger.md`
