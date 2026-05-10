# Supabase-First FastAPI Dashboard Rewrite

The VPS dashboard rewrite will replace the local plain HTTP dashboard with one compact FastAPI production web layer. The migration target is Supabase-first: Supabase Postgres for metadata, Supabase Storage for artifacts, Supabase Auth for users, and a separate worker for long-running pipeline execution.

## Decisions

- Production metadata storage is Supabase Postgres. Run metadata, run status, settings versions, manual run records, curation records, selected videos, raw videos, and output metadata move to Supabase.
- SQLite is removed from the new dashboard runtime. It should not remain as local development storage or a second supported dashboard store. A later migration slice may read legacy SQLite only as a one-time import source if needed.
- Large artifacts use Supabase Storage. Source videos, generated reports, workbooks, raw scrape JSON, evidence snapshots, Gemini responses, and other large files are stored as objects, with metadata rows in Supabase Postgres.
- Authentication uses Supabase Auth. Dashboard user identity should flow into `created_by`, `updated_by`, manual-run trigger user, curation author, and other audit fields.
- Rendering uses server-rendered Jinja templates. Report Markdown may be rendered server-side and inserted into a Jinja page, but the app should not keep large Python HTML string renderers as the main presentation layer.
- The new Jinja dashboard should preserve the legacy dashboard's visual language: color theme, dense operational layout, navigation feel, card/table styling, buttons, status pills, and logo treatment. This rewrite is architectural, not a redesign.
- Batch execution runs outside the FastAPI request process. FastAPI writes authenticated manual-run requests to Supabase; a separate Python worker managed by `systemd` claims queued jobs, enforces active-run locking, runs the pipeline, uploads artifacts to Supabase Storage, and updates status.
- Existing dashboard code gets a strict migration cleanup. Keep only useful domain rules and small helpers. Rewrite web, auth, storage, route, persistence, and template boundaries around FastAPI and Supabase. Delete the old `BaseHTTPRequestHandler` server, SQLite store, SQLite-specific tests, and Python HTML rendering modules after parity.
- Keep the implementation compact and powerful. Do not add placeholder modules, generic repositories, repository-per-table layers, broad adapters, or empty abstractions before the code proves they are needed.

## Route Map

Canonical FastAPI routes use clean resource-style paths. Temporary redirects from old dashboard paths are allowed during transition, but these are the target routes:

| Method | Route | Auth | Purpose |
|---|---|---|---|
| `GET` | `/` | Yes | Dashboard overview. |
| `GET` | `/healthz` | No | Lightweight uptime check. |
| `GET` | `/login` | No | Supabase Auth login page. |
| `POST` | `/login` | No | Supabase Auth sign-in. |
| `POST` | `/logout` | Yes | Sign out. |
| `GET` | `/runs` | Yes | Run history list. |
| `GET` | `/runs/{run_id}` | Yes | Run detail, status, and artifacts. |
| `POST` | `/runs` | Yes | Trigger an authenticated manual run. |
| `GET` | `/reports` | Yes | Report list or latest report redirect. |
| `GET` | `/reports/{run_id}` | Yes | Report viewer for one run. |
| `GET` | `/settings` | Yes | Scrape settings and version history. |
| `POST` | `/settings` | Yes | Save a new settings version. |
| `POST` | `/settings/{version}/rollback` | Yes | Roll back settings to a prior version. |
| `POST` | `/videos/{video_id}/curation` | Yes | Save curation labels and notes. |
| `GET` | `/exports/raw-videos.csv` | Yes | Download raw video CSV export. |
| `GET` | `/exports/run-summaries.csv` | Yes | Download run summary CSV export. |
| `GET` | `/artifacts/{artifact_id}` | Yes | Signed download or proxy for a Supabase Storage artifact. |
| `GET` | `/static/{path}` | No | Static dashboard assets. |

## Module Map

```text
dashboard/
  app.py                 FastAPI app factory, middleware, route registration
  config.py              environment config and runtime settings
  auth.py                Supabase Auth session/user dependency
  supabase_client.py     Supabase Postgres and Storage client boundary
  runtime.py             enqueue manual runs and active-run guard
  worker.py              queue polling, job claim, pipeline execution

  routes/
    overview.py
    runs.py
    reports.py
    settings.py
    curation.py
    exports.py
    artifacts.py

  templates/
    base.html
    login.html
    overview.html
    runs.html
    run_detail.html
    report.html
    settings.html

  assets/
    dashboard.css
    dashboard.js
    nattome-logo.png
```

This is a target shape, not a license to scaffold empty files. Later implementation slices should add files only when they carry real behavior.
