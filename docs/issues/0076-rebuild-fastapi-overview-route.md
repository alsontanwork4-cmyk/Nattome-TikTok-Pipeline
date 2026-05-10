# Rebuild FastAPI Overview Route

Labels: needs-triage
Type: AFK

## What to build

Rebuild the latest run overview page through the new FastAPI dashboard architecture. This should be the first real page route and should establish the compact server-rendered layout pattern for the rest of the rewrite.

The completed slice should let a user open `/` in the FastAPI app and see the current latest-run overview using real dashboard data or the documented empty state.

## Acceptance criteria

- [ ] Implement `GET /` in the FastAPI app.
- [ ] Render a production dashboard shell with top navigation or sidebar appropriate for the rewrite.
- [ ] Display latest run overview data when available.
- [ ] Display a clear empty state when no run data exists.
- [ ] Reuse useful existing non-web data loading logic where practical.
- [ ] Do not depend on `BaseHTTPRequestHandler` or the old `dashboard.web_server` request path.
- [ ] Add FastAPI route tests for populated and empty overview states.
- [ ] Verify the page in browser or with a rendered HTML smoke check.

## Blocked by

- `docs/issues/0075-bootstrap-fastapi-dashboard-health-slice.md`

