# Remove Legacy Dashboard Server And SQLite Runtime

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Remove the replaced plain Python dashboard server and SQLite runtime after the Supabase-first FastAPI dashboard reaches parity. This is the cleanup gate that keeps the final codebase compact and prevents two dashboard architectures or stores from living side by side.

The completed slice should delete old server code, SQLite runtime code, obsolete tests, and outdated docs that conflict with the FastAPI/Supabase rewrite.

## Acceptance criteria

- [ ] Delete or retire the old `BaseHTTPRequestHandler` dashboard server code.
- [ ] Delete SQLite runtime/store code that is no longer needed after Supabase parity.
- [ ] Remove obsolete tests that only protect the old request handler or SQLite runtime implementation.
- [ ] Remove or supersede docs that prohibit FastAPI or instruct production users to run the old server.
- [ ] Update `dashboard.web` imports or replacement entrypoint documentation to point at the FastAPI app.
- [ ] Update README and VPS docs to reference only the FastAPI/Supabase production dashboard path.
- [ ] `rg` confirms no production reference to the retired server command remains.
- [ ] `rg` confirms no new dashboard runtime path initializes SQLite.
- [ ] The FastAPI route tests pass.
- [ ] The dashboard-related test suite passes after deletion.

## Blocked by

- `docs/issues/0080-build-overview-from-supabase-runs.md`
- `docs/issues/0082-rebuild-reports-and-csv-exports-from-supabase.md`
- `docs/issues/0083-rebuild-settings-and-curation-on-supabase.md`
- `docs/issues/0084-add-worker-backed-manual-run-trigger.md`
- `docs/issues/0085-add-one-time-legacy-artifact-import.md`
- `docs/issues/0086-add-supabase-vps-deployment-path.md`
