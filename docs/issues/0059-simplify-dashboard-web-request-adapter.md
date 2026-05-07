# Simplify Dashboard Web Request Adapter

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0052-deepen-dashboard-codebase-architecture.md`

## What to build

Simplify the local dashboard HTTP request adapter by replacing repetitive GET and POST branching with clearer route/action dispatch and shared helpers. Preserve the lightweight local HTTP server, current routes, redirects, validation error behavior, export responses, and page rendering.

## Acceptance criteria

- [ ] GET page and export routing is represented through clearer dispatch instead of repeated conditional branches.
- [ ] POST form action routing is represented through clearer dispatch instead of repeated conditional branches.
- [ ] Shared helpers handle request body parsing, form parsing, validation error pages, and redirects.
- [ ] Existing routes remain unchanged.
- [ ] Existing redirects remain unchanged.
- [ ] Existing validation error status codes and response bodies remain unchanged.
- [ ] Existing export response content types, filenames, and bodies remain unchanged.
- [ ] The dashboard remains on the lightweight local HTTP server.
- [ ] No Flask, FastAPI, JavaScript frontend framework, or other web framework is introduced.
- [ ] Tests cover route behavior, form action behavior, validation errors, redirects, exports, and page rendering.
- [ ] Existing dashboard tests remain green.

## Blocked by

- `docs/issues/0054-localize-store-access-for-small-dashboard-callers.md`
- `docs/issues/0056-centralize-dashboard-derived-refresh.md`
- `docs/issues/0057-centralize-nattome-scoring-vocabulary.md`
