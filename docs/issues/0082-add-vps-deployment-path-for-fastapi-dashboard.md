# Add VPS Deployment Path For FastAPI Dashboard

Labels: needs-triage
Type: AFK

## What to build

Add the VPS deployment path for the FastAPI dashboard so the app can run behind HTTPS, restart automatically, and use documented environment variables and backups.

The completed slice should give the owner enough concrete deployment material to run the dashboard on a VPS without relying on the old local server command.

## Acceptance criteria

- [ ] Add FastAPI VPS deployment documentation.
- [ ] Provide a `systemd` service example for the app.
- [ ] Provide an Nginx or Caddy reverse proxy example.
- [ ] Document required environment variables for workspace, auth, database, artifact storage, and production mode.
- [ ] Document the `uvicorn` production command.
- [ ] Document database backup expectations.
- [ ] Document artifact backup expectations.
- [ ] Production docs do not instruct users to run the old dashboard server.

## Blocked by

- `docs/issues/0075-bootstrap-fastapi-dashboard-health-slice.md`
- `docs/issues/0078-add-authenticated-manual-run-trigger.md`
- `docs/issues/0081-add-production-storage-for-run-metadata.md`

