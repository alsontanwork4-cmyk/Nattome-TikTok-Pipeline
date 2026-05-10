# Remove Legacy Dashboard Server

Labels: needs-triage
Type: AFK

## What to build

Remove the replaced plain Python dashboard server after the FastAPI rewrite reaches parity. This issue is the cleanup gate that keeps the final codebase compact and prevents two dashboard architectures from living side by side.

The completed slice should delete old server code, obsolete tests, and outdated docs that conflict with the FastAPI rewrite.

## Acceptance criteria

- [ ] Delete or retire the old `BaseHTTPRequestHandler` dashboard server code.
- [ ] Remove obsolete tests that only protect the old request handler implementation.
- [ ] Remove or supersede docs that prohibit FastAPI or instruct production users to run the old server.
- [ ] Update `dashboard.web` imports or replacement entrypoint documentation to point at the FastAPI app.
- [ ] Update README and VPS docs to reference only the FastAPI production dashboard path.
- [ ] `rg` confirms no production reference to the retired server command remains.
- [ ] The FastAPI route tests pass.
- [ ] The dashboard-related test suite passes after deletion.

## Blocked by

- `docs/issues/0076-rebuild-fastapi-overview-route.md`
- `docs/issues/0077-rebuild-fastapi-run-history-and-status.md`
- `docs/issues/0078-add-authenticated-manual-run-trigger.md`
- `docs/issues/0079-rebuild-fastapi-settings-and-curation-flows.md`
- `docs/issues/0080-rebuild-fastapi-reports-and-csv-exports.md`
- `docs/issues/0081-add-production-storage-for-run-metadata.md`
- `docs/issues/0082-add-vps-deployment-path-for-fastapi-dashboard.md`

