# Bootstrap FastAPI Dashboard Health Slice

Labels: needs-triage
Type: AFK

## What to build

Add the first runnable FastAPI dashboard slice for the VPS rewrite. The slice should introduce the new app entry point, environment-based config, static serving baseline, health check, and tests without rebuilding all dashboard pages yet.

The completed slice should prove that the new FastAPI app can start, serve `/healthz`, and run through the repo's normal test path.

## Acceptance criteria

- [ ] Add a FastAPI app entry point, for example `dashboard/app.py`.
- [ ] Add a production run command using `uvicorn` or document the exact command.
- [ ] Add environment-based configuration for workspace path and production mode.
- [ ] Add `/healthz` returning a lightweight successful response.
- [ ] Add a static asset serving baseline for dashboard CSS/JS/images.
- [ ] Add focused tests for app startup and `/healthz`.
- [ ] Add or update requirements so FastAPI and the ASGI server are installed.
- [ ] Existing non-dashboard tests are not broken by the new app.

## Blocked by

- `docs/issues/0074-lock-fastapi-dashboard-rewrite-decisions.md`

