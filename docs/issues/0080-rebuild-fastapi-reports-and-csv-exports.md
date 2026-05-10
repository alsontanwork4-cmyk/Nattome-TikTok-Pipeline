# Rebuild FastAPI Reports And CSV Exports

Labels: needs-triage
Type: AFK

## What to build

Rebuild report viewing and CSV export routes in the FastAPI dashboard. The slice should let a remote user inspect selected run reports and download raw video or run summary CSVs from the hosted app.

The completed slice should preserve the reporting/export utility of the current dashboard without using the old request handler.

## Acceptance criteria

- [ ] Implement `GET /report` in the FastAPI app.
- [ ] Report page loads the selected report for a run.
- [ ] Missing report artifacts show a clear empty state.
- [ ] Implement raw video CSV export route.
- [ ] Implement run summary CSV export route.
- [ ] Download responses set correct content type and filename.
- [ ] Export routes use the new FastAPI response path, not `BaseHTTPRequestHandler`.
- [ ] Add tests for report present, report missing, and both CSV downloads.

## Blocked by

- `docs/issues/0076-rebuild-fastapi-overview-route.md`
- `docs/issues/0077-rebuild-fastapi-run-history-and-status.md`

