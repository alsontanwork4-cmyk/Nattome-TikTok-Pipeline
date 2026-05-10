# Rebuild FastAPI Run History And Status

Labels: needs-triage
Type: AFK

## What to build

Rebuild run history and run detail through FastAPI, including visible batch run status. The page should make normal pipeline state understandable from the browser without requiring SSH.

The completed slice should show historical runs, selected run detail, output links, and status values such as queued, running, succeeded, and failed.

## Acceptance criteria

- [ ] Implement `GET /run-history` in the FastAPI app.
- [ ] Show the run list with newest runs first.
- [ ] Show selected run detail, including start time, end time, duration, output paths, and status.
- [ ] Display queued, running, succeeded, failed, and canceled states if canceled is supported.
- [ ] Failed runs expose an error summary without rendering secrets or full environment dumps.
- [ ] Latest run status is visible from the run history page.
- [ ] Add tests for each supported status display.
- [ ] Do not depend on the old dashboard request handler.

## Blocked by

- `docs/issues/0075-bootstrap-fastapi-dashboard-health-slice.md`
- `docs/issues/0076-rebuild-fastapi-overview-route.md`

