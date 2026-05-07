# Localize Store Access For Small Dashboard Callers

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0052-deepen-dashboard-codebase-architecture.md`

## What to build

Deepen the dashboard store module with small persistence helpers, then migrate the smaller direct database callers through those helpers. Keep SQLite as the only storage adapter, keep feature-specific SQL in feature modules, and remove the visible SQLite path from the dashboard topbar by replacing it with operational status.

## Acceptance criteria

- [ ] The store module exposes a dashboard connection helper that initializes the store and defaults to row-style access.
- [ ] The store module exposes JSON load behavior with explicit caller-provided fallbacks.
- [ ] The store module exposes deterministic JSON dump behavior.
- [ ] Smaller direct database callers use the new store helpers for connection setup and JSON behavior where safe.
- [ ] Callers keep explicit commit and close behavior.
- [ ] No connection context manager is introduced.
- [ ] No repository class per table is introduced.
- [ ] The dashboard topbar no longer shows the SQLite path.
- [ ] The dashboard topbar shows operational status such as Pipeline ready and Local workspace.
- [ ] Tests cover store helper behavior, migrated callers, and topbar output.
- [ ] Existing dashboard tests remain green.

## Blocked by

- `docs/issues/0053-characterize-dashboard-architecture-behavior.md`
