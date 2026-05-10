# PRD: VPS FastAPI Dashboard Rewrite

## Introduction

The current Nattome TikTok dashboard started as a lightweight local Python HTTP server. It now needs to become a VPS-hosted control panel for batch analysis runs, run history, reports, scrape settings, curation, and persistent storage.

The preferred direction is a full dashboard rewrite, not a gradual long-term coexistence with the current local server. The goal is a simple, compact, powerful FastAPI application that keeps the valuable domain logic where it is still useful, but removes the old plain-HTTP dashboard once the replacement is complete.

This is still a Python rewrite, not a rewrite into another language. FastAPI becomes the only production web layer. The final codebase should avoid dead legacy routes, duplicate request handlers, and two dashboard architectures living side by side.

## Goals

- Replace the current plain Python dashboard server with a compact FastAPI app.
- Host the dashboard and batch analysis control surface reliably on a VPS.
- Remove legacy dashboard server code after FastAPI reaches feature parity.
- Keep or extract useful business logic, but rewrite the web layer cleanly.
- Provide persistent storage for run metadata, settings, curation, and batch status.
- Support authentication before exposing the dashboard over the internet.
- Keep the first production version server-rendered unless a separate frontend becomes clearly necessary.
- Make the final system easy to understand, deploy, debug, and extend.

## Product Principles

- **One web architecture:** FastAPI is the production web layer. The old `BaseHTTPRequestHandler` dashboard should not remain as a second maintained path.
- **Compact over clever:** Prefer direct route modules and clear data access over generic controllers, repositories, adapters, or framework-heavy abstractions.
- **Powerful where it matters:** Invest complexity only in batch orchestration, storage durability, auth, exports, and run visibility.
- **No dead code:** Remove replaced dashboard code, routes, tests, and docs once the FastAPI version is verified.
- **Python continuity:** Reuse Python pipeline/domain code when it reduces risk, but do not preserve old web code just because it exists.

## User Stories

### US-001: Create the FastAPI application shell

**Description:** As a maintainer, I want a new FastAPI app to become the only dashboard web layer so that the hosted VPS app has a clean foundation.

**Acceptance Criteria:**

- [ ] Add a FastAPI app entry point, for example `dashboard/app.py`.
- [ ] Add a production run command using `uvicorn`.
- [ ] Add a `/healthz` endpoint for service monitoring.
- [ ] Add app configuration from environment variables.
- [ ] Add tests for app startup and health check.

### US-002: Rebuild core dashboard routes

**Description:** As a dashboard user, I want the hosted dashboard to provide the same core sections in a cleaner FastAPI structure so that I can operate the pipeline remotely.

**Acceptance Criteria:**

- [ ] Implement `/` for latest run overview.
- [ ] Implement `/report` for selected run report viewing.
- [ ] Implement `/run-history` for historical runs and run detail.
- [ ] Implement `/scrape-settings` for current settings and settings edits.
- [ ] Use FastAPI route functions instead of the old manual request handler.
- [ ] Verify pages in browser.

### US-003: Replace the old dashboard server

**Description:** As a maintainer, I want the old plain Python HTTP server removed after the FastAPI routes are complete so that the repo does not carry dead dashboard architecture.

**Acceptance Criteria:**

- [ ] Remove or retire `dashboard/web_server.py` after FastAPI route parity is verified.
- [ ] Update `dashboard/web.py` or replace it with the new FastAPI entrypoint/export surface.
- [ ] Remove tests that only protect the old `BaseHTTPRequestHandler` implementation.
- [ ] Add tests that protect the new FastAPI behavior.
- [ ] Update docs that still instruct users to run the old server.
- [ ] No production docs reference the old dashboard server.

### US-004: Keep useful domain logic without preserving old web code

**Description:** As a maintainer, I want to reuse useful pipeline and dashboard data logic where it is clean, while allowing old HTML/request code to be rewritten.

**Acceptance Criteria:**

- [ ] Review existing modules and classify them as keep, rewrite, or delete.
- [ ] Keep useful non-web modules such as run loading, settings validation, exports, manual runs, and report discovery where practical.
- [ ] Rewrite request handling, auth, response handling, and route composition in FastAPI.
- [ ] Remove old helper functions that only exist for the deleted server.
- [ ] Document the final module map.

### US-005: Add production authentication

**Description:** As the owner, I want the VPS dashboard protected by authentication so that run controls and batch results are not publicly accessible.

**Acceptance Criteria:**

- [ ] Dashboard pages require authentication in production.
- [ ] Mutating routes require authentication.
- [ ] `/healthz` may remain unauthenticated for uptime checks.
- [ ] Secrets are configured through environment variables.
- [ ] Tests cover unauthenticated, authenticated, and mutating-route access.

### US-006: Add persistent production storage

**Description:** As a dashboard user, I want run history, run status, settings, and curation to persist reliably so that batch analysis results survive restarts and can be queried over time.

**Acceptance Criteria:**

- [ ] Define production tables for runs, run outputs, selected videos, raw videos, curation, settings versions, and manual runs.
- [ ] Choose initial production storage: local Postgres, Supabase Postgres, or SQLite with a clear upgrade path.
- [ ] Store large artifacts as files or object-storage objects, not database blobs.
- [ ] Store artifact metadata in the database.
- [ ] Add backup and restore notes.

### US-007: Track batch run status

**Description:** As a dashboard user, I want to see whether a batch analysis run is queued, running, succeeded, or failed so that I do not need SSH access to understand pipeline state.

**Acceptance Criteria:**

- [ ] Run status includes queued, running, succeeded, failed, and canceled if supported.
- [ ] Run detail shows start time, end time, duration, output paths, and error summary.
- [ ] Failed runs do not expose secrets or full environment dumps.
- [ ] Latest status is visible from the dashboard.
- [ ] Tests cover each status display.

### US-008: Trigger manual batch runs safely

**Description:** As a dashboard user, I want to start a full pipeline run from the hosted dashboard without accidentally launching duplicate long-running jobs.

**Acceptance Criteria:**

- [ ] Implement authenticated manual run trigger.
- [ ] Prevent duplicate active full-pipeline runs.
- [ ] Record trigger user, trigger time, run type, status, and output metadata.
- [ ] Long-running execution does not block the web request until completion.
- [ ] Trigger failures produce a visible, actionable error.

### US-009: Rebuild settings and curation flows

**Description:** As a dashboard user, I want scrape settings and video curation to work in the new dashboard so that production decisions are captured.

**Acceptance Criteria:**

- [ ] View active scrape settings.
- [ ] Save a new settings version.
- [ ] Roll back to a prior settings version.
- [ ] Save video curation labels and notes.
- [ ] Validate form data server-side.
- [ ] Tests cover save, rollback, validation, and curation persistence.

### US-010: Serve reports, exports, and artifacts

**Description:** As a dashboard user, I want to read reports and download CSV exports from the hosted dashboard so that batch analysis outputs are usable outside the app.

**Acceptance Criteria:**

- [ ] Report page can load the selected report for a run.
- [ ] Raw video CSV export works.
- [ ] Run summary CSV export works.
- [ ] Download routes set correct content type and filename.
- [ ] Missing artifacts show a clear empty state.

### US-011: Add VPS deployment support

**Description:** As a maintainer, I want a repeatable VPS deployment so that the app runs behind HTTPS and restarts automatically.

**Acceptance Criteria:**

- [ ] Add deployment documentation for FastAPI on VPS.
- [ ] Provide a `systemd` service example.
- [ ] Provide an Nginx or Caddy reverse proxy example.
- [ ] Document required environment variables.
- [ ] Document database and artifact backup expectations.

### US-012: Remove dead legacy code

**Description:** As a maintainer, I want replaced dashboard code deleted so that future work happens in one compact codebase.

**Acceptance Criteria:**

- [ ] Delete old server code after FastAPI parity.
- [ ] Delete obsolete old-server tests.
- [ ] Delete obsolete architecture-contract docs that prohibit FastAPI.
- [ ] Update import paths and docs.
- [ ] `rg` confirms no production reference to the retired server command.
- [ ] Test suite passes after deletion.

## Functional Requirements

- FR-1: The dashboard must run as a FastAPI app.
- FR-2: The production app must be served by `uvicorn` or a compatible ASGI server.
- FR-3: The app must provide routes for overview, report, run history, scrape settings, exports, health check, curation, and manual run trigger.
- FR-4: The app must require authentication for dashboard pages and mutating actions in production.
- FR-5: The app must store run metadata, run status, settings versions, and curation data durably.
- FR-6: The app must store large artifacts outside the relational database.
- FR-7: The app must expose enough run status detail to operate the pipeline without SSH for normal cases.
- FR-8: Manual run triggers must be protected against duplicate active runs.
- FR-9: Settings changes must be versioned and rollbackable.
- FR-10: CSV exports must remain available.
- FR-11: Deployment must support HTTPS through a reverse proxy.
- FR-12: Configuration must come from environment variables or deployment files, not hardcoded local paths.
- FR-13: The old plain HTTP server must be removed after FastAPI feature parity.
- FR-14: Tests must cover the new FastAPI app, storage behavior, auth behavior, run status, and core dashboard pages.

## Non-Goals

- Do not rewrite the pipeline in another language.
- Do not keep two production dashboard servers.
- Do not build a public SaaS or multi-tenant product in this version.
- Do not introduce React, Vue, or a separate frontend unless server-rendered HTML becomes limiting.
- Do not store source videos or large reports directly in Postgres.
- Do not add Kubernetes or complex orchestration for the first VPS version.
- Do not create generic repository or adapter layers without a concrete need.
- Do not preserve old dashboard architecture tests that conflict with the FastAPI rewrite.

## Design Considerations

- The first FastAPI version should probably use server-rendered HTML for compactness.
- Templates may be introduced if they make the new code smaller and easier to read than large Python f-strings.
- The dashboard should feel like an operational control panel: dense, clear, and focused.
- Run status should be visible near the top of the relevant pages.
- Mutating actions should provide direct success or error feedback.
- Secrets, tokens, cookies, and full environment values must never be rendered.

## Technical Considerations

### Likely keep or adapt

- `dashboard/indexer.py`
- `dashboard/run_history.py`
- `dashboard/settings.py`
- `dashboard/exports.py`
- `dashboard/manual_runs.py`
- `dashboard/report_view.py`
- `dashboard/store.py`, if SQLite remains part of local/dev mode

### Likely rewrite

- `dashboard/web.py`
- `dashboard/web_server.py`
- `dashboard/web_layout.py`
- `dashboard/web_components.py`
- `dashboard/web_overview.py`
- `dashboard/web_report.py`
- `dashboard/web_run_history.py`
- `dashboard/web_settings.py`

Some rendering logic can be copied or translated, but the final structure should belong to FastAPI, not the old server.

### Proposed new structure

```text
dashboard/
  app.py                 FastAPI app factory and route registration
  config.py              Environment-based app settings
  auth.py                Authentication helpers
  routes/
    overview.py
    reports.py
    run_history.py
    settings.py
    exports.py
    manual_runs.py
  templates/
    base.html
    overview.html
    report.html
    run_history.html
    settings.html
  static/
    dashboard.css
    dashboard.js
  storage/
    connection.py
    schema.py
  runtime.py             Batch trigger and active-run coordination
```

This structure is a proposal. Implementation should keep it compact and avoid empty folders or placeholder abstractions.

## Storage Decision

The preferred production storage should be decided before implementation begins.

Recommended path:

1. Use Postgres/Supabase for production run metadata, settings versions, manual runs, and curation.
2. Use VPS disk or Supabase Storage for large artifacts.
3. Keep SQLite only for local development or one-time migration, not as the long-term production source of truth.

Candidate tables:

- `runs`
- `run_outputs`
- `raw_videos`
- `selected_videos`
- `video_curation`
- `scrape_settings_versions`
- `manual_runs`

Large artifacts should be referenced by metadata: path, storage provider, size, checksum if available, created time, and run id.

## Implementation Plan

### Phase 1: Design the new app map

- Decide storage backend for production.
- Decide whether to use templates.
- Define final module map.
- Define route map.
- Identify old files to delete after parity.

### Phase 2: Build FastAPI foundation

- Add FastAPI app.
- Add config.
- Add health check.
- Add static file serving.
- Add base layout/template.
- Add initial tests.

### Phase 3: Rebuild pages and actions

- Rebuild overview.
- Rebuild reports.
- Rebuild run history.
- Rebuild scrape settings.
- Rebuild curation save.
- Rebuild exports.
- Rebuild manual run trigger.

### Phase 4: Add auth and production storage

- Add authentication.
- Add production database schema.
- Add storage access code.
- Add migration/import path from current artifacts or SQLite.
- Add backup documentation.

### Phase 5: Add VPS deployment

- Add `systemd` service example.
- Add reverse proxy docs.
- Add env var docs.
- Verify the app runs on the VPS path layout.

### Phase 6: Remove legacy dashboard

- Delete old plain HTTP server code.
- Delete obsolete tests.
- Delete obsolete docs that forbid FastAPI.
- Update commands and imports.
- Run the full dashboard test suite.

## Success Metrics

- The dashboard runs on the VPS through FastAPI and HTTPS.
- A user can view runs, reports, settings, and exports remotely.
- A user can trigger and monitor a batch run without SSH.
- Auth protects the dashboard before public exposure.
- Production run metadata survives service restarts.
- The old dashboard server code is removed after replacement.
- The final dashboard codebase is smaller or easier to navigate than the old web module set.
- There is one production web architecture.

## Risks and Mitigations

- **Risk:** Full rewrite takes longer than expected.
  **Mitigation:** Keep the route list small and rebuild only production-critical pages first.

- **Risk:** Useful domain logic gets thrown away unnecessarily.
  **Mitigation:** Classify files before deleting: keep, adapt, rewrite, delete.

- **Risk:** The app becomes over-abstracted.
  **Mitigation:** Avoid generic repositories, adapters, and empty layers until the code proves they are needed.

- **Risk:** Hosted dashboard exposes sensitive controls.
  **Mitigation:** Add auth before production exposure and protect all mutating routes.

- **Risk:** Batch run trigger creates duplicate or stuck jobs.
  **Mitigation:** Add active-run lock/status tracking and visible failure states.

- **Risk:** Large artifacts overload the database.
  **Mitigation:** Store large files in disk/object storage and keep metadata in the database.

## Open Questions

- Should production storage be Supabase Postgres immediately, or local Postgres on the VPS first?
- Should authentication be simple owner password first, or Supabase Auth from the start?
- Should server-rendered templates replace Python f-string HTML immediately?
- Should batch execution run inside the FastAPI app process, a separate worker process, or a `systemd` job?
- Which old dashboard modules should be deleted outright versus copied into the new route/template structure?
- Should SQLite remain supported for local development after the production rewrite?

