# Add Supabase Auth Gate

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Add Supabase Auth as the dashboard authentication boundary. The slice should let users sign in and out, protect dashboard pages and mutating routes, and expose authenticated user identity to later persistence flows.

The completed slice should make `/healthz` public while requiring a Supabase-authenticated user for the dashboard shell.

## Acceptance criteria

- [ ] Implement `GET /login` and `POST /login` for Supabase Auth sign-in.
- [ ] Implement `POST /logout`.
- [ ] Add a Supabase Auth user/session dependency for protected routes.
- [ ] Protect dashboard pages and mutating dashboard routes by default.
- [ ] Keep `/healthz` unauthenticated.
- [ ] Expose authenticated user identity for audit fields such as `created_by`, `updated_by`, trigger user, and curation author.
- [ ] Add tests for unauthenticated access, authenticated access, login failure, and logout.
- [ ] The login page follows the legacy dashboard visual theme.

## Blocked by

- `docs/issues/0075-bootstrap-supabase-first-fastapi-shell.md`
- `docs/issues/0076-port-legacy-dashboard-visual-theme-to-jinja-shell.md`
