# Superseded Dashboard Architecture Contract Verification

This document verified the former local dashboard architecture for issue `0060`.
It is retained only as historical context.

The active verification target is the Supabase-first FastAPI dashboard described
by:

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`
- `docs/supabase-dashboard-data-contract.md`
- `docs/vps-dashboard-deployment.md`

Current checks should protect the FastAPI entrypoint, Supabase data contract,
Supabase Auth gate, worker-backed manual run contract, and one-time legacy
artifact import path. They should not protect the retired local request handler
or local dashboard SQLite runtime.
