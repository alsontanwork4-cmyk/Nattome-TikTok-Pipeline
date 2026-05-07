# Bootstrap Local Dashboard Shell

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Create the initial local web dashboard foundation for the Nattome marketer-facing Scrape Quality Dashboard. The slice should produce a runnable local web app shell with a dashboard-owned SQLite state store, a basic navigation structure, and an empty Latest Run Overview route that can be expanded by later slices.

This slice should establish the application shape without implementing artifact indexing, scoring, run orchestration, or marketer workflows yet.

## Acceptance criteria

- [ ] A local web app can be started from the repo with documented development commands.
- [ ] The app has a basic shell with navigation placeholders for Overview, Scraped Content, Run History, Scrape Settings, Recommendations, Pattern Library, Nattome POV Library, and Pipeline Architecture.
- [ ] A dashboard-owned SQLite database is initialized in a predictable local path.
- [ ] Mutable dashboard records have a consistent convention for `created_by`, `updated_by`, `created_at`, and `updated_at`.
- [ ] The initial Overview route renders without requiring Apify, Gemini, or existing run artifacts.
- [ ] Basic smoke tests verify the app shell can load and the SQLite store can initialize.

## Blocked by

None - can start immediately
