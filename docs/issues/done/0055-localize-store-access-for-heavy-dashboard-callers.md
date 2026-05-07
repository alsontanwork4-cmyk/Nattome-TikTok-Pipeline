# Localize Store Access For Heavy Dashboard Callers

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0052-deepen-dashboard-codebase-architecture.md`

## What to build

Continue the persistence locality work by migrating heavier dashboard modules to the store helpers where safe. Preserve feature-specific SQL and current behavior for Run History, Search, exports, recommendations, Pattern Library, Nattome POV Library, Scrape Quality, Pipeline Health, and architecture browsing.

## Acceptance criteria

- [ ] Heavy dashboard modules no longer duplicate direct store initialization and connection setup where the store helper is suitable.
- [ ] Duplicate JSON helpers are removed only where the explicit fallback behavior matches existing behavior.
- [ ] Feature-specific SQL remains near the feature modules.
- [ ] No full repository class per table is introduced.
- [ ] No storage adapter abstraction is introduced.
- [ ] Public dashboard imports remain stable.
- [ ] Run History behavior remains unchanged.
- [ ] Search and facet behavior remains unchanged.
- [ ] Export output shape remains unchanged.
- [ ] Pattern Library and Nattome POV Library behavior remains unchanged.
- [ ] Recommendation, Scrape Quality, Pipeline Health, and architecture browser behavior remains unchanged.
- [ ] Existing dashboard tests remain green.

## Blocked by

- `docs/issues/0054-localize-store-access-for-small-dashboard-callers.md`
