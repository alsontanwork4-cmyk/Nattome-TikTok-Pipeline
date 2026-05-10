# Superseded Dashboard Architecture Deepening PRD

This PRD described the former local dashboard architecture before the
Supabase-first FastAPI rewrite. It is retained only as historical context for
issues `0053` through `0060`.

The active dashboard architecture is now defined by:

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`
- `docs/supabase-dashboard-data-contract.md`
- `docs/vps-dashboard-deployment.md`

Current production direction:

- FastAPI is the dashboard web layer.
- Supabase Postgres is the dashboard metadata store.
- Supabase Storage is the large artifact store.
- Supabase Auth protects dashboard pages and mutating actions.
- A separate worker handles long-running pipeline execution.

Do not use this superseded PRD to justify adding local dashboard SQLite runtime
support, the old plain HTTP request handler, or production instructions for the
retired dashboard server.
