# Bootstrap Supabase-First FastAPI Shell

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Add the first runnable FastAPI dashboard slice for the Supabase-first rewrite. The slice should introduce the app entry point, environment configuration, static asset serving, base Jinja template, `/healthz`, and focused tests without rebuilding full dashboard pages yet.

The completed slice should prove that the new app starts without the old `BaseHTTPRequestHandler` server or SQLite runtime.

## Acceptance criteria

- [ ] Add a FastAPI app entry point, for example `dashboard/app.py`.
- [ ] Add environment-based configuration for runtime mode, Supabase settings, and workspace paths needed during migration.
- [ ] Add `/healthz` returning a lightweight successful response without authentication.
- [ ] Add Jinja template setup with a base template.
- [ ] Serve dashboard static assets from the FastAPI app.
- [ ] Add or update requirements so FastAPI, the ASGI server, and Jinja are installed.
- [ ] Add focused tests for app startup and `/healthz`.
- [ ] The new shell does not import `dashboard.web_server` or initialize SQLite.

## Blocked by

- `docs/issues/0074-lock-fastapi-dashboard-rewrite-decisions.md`
