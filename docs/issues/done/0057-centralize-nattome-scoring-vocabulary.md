# Centralize Nattome Scoring Vocabulary

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0052-deepen-dashboard-codebase-architecture.md`

## What to build

Create one scoring vocabulary module for shared Nattome dashboard scoring concepts, then migrate Scrape Quality, Run History, Search, and web display code to use it. Nattome relevance, weighted engagement, freshness, and score or band text should mean the same thing everywhere they appear.

## Acceptance criteria

- [ ] A scoring module owns Nattome relevance terms and Nattome relevance computation.
- [ ] The scoring module owns weighted engagement computation.
- [ ] The scoring module owns freshness behavior shared by dashboard pages.
- [ ] The scoring module owns shared score or band text where appropriate.
- [ ] Scrape Quality behavior remains unchanged after migration.
- [ ] Run History scoring and metric behavior remains unchanged after migration.
- [ ] Search relevance, engagement, freshness, and facet behavior remains unchanged after migration.
- [ ] Web-rendered score and engagement text remains unchanged after migration.
- [ ] Tests verify scoring parity with representative raw videos and Batch Analysis Run records.
- [ ] Existing dashboard tests remain green.

## Blocked by

- `docs/issues/0055-localize-store-access-for-heavy-dashboard-callers.md`
