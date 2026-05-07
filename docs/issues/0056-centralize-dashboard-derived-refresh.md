# Centralize Dashboard Derived Refresh

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0052-deepen-dashboard-codebase-architecture.md`

## What to build

Add one dashboard refresh module that owns automatic derived refresh orchestration for artifact indexing, Scrape Quality score recomputation, and Pipeline Health recomputation. Dashboard read paths should keep automatic refresh behavior, but page modules should request refresh through the shared module instead of owning the refresh sequence.

## Acceptance criteria

- [ ] A refresh module orchestrates artifact indexing, Scrape Quality recomputation, and Pipeline Health recomputation.
- [ ] Overview, Search, Run History, and related read paths use the refresh module where appropriate.
- [ ] Automatic refresh behavior remains in place for local artifact-driven dashboard workflows.
- [ ] Refresh callers can express intent or scope without duplicating the full refresh sequence.
- [ ] No manual refresh requirement is introduced.
- [ ] Existing indexed artifact, Scrape Quality, and Pipeline Health behavior remains unchanged.
- [ ] Tests verify that page-level refresh requests still update derived dashboard data.
- [ ] Existing dashboard tests remain green.

## Blocked by

- `docs/issues/0055-localize-store-access-for-heavy-dashboard-callers.md`
