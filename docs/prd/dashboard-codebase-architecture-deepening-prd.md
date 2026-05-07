# Dashboard Codebase Architecture Deepening PRD

## Problem Statement

The local Nattome dashboard has grown from a marketer-facing Scrape Quality control room into a broad operational surface for raw scraped videos, Batch Analysis Runs, Pipeline Health, run history, recommendations, Pattern Library entries, Nattome POV entries, exports, search, and architecture browsing.

The current codebase is not broken and is not currently high regression risk. It has focused dashboard tests and coherent feature modules. However, the dashboard is starting to accumulate architectural friction. Persistence lifecycle, SQLite path knowledge, JSON fallback behavior, automatic derived-data refresh, Nattome relevance scoring, weighted engagement scoring, and web request handling are repeated across many modules. Presentation code also carries a large inline theme inside the page layout module.

This makes the dashboard feel more bloated than it needs to be. It also raises future regression risk because a small behavior change can require edits across multiple feature modules, and the same dashboard concept can drift between Overview, Search, Run History, Scrape Quality, and web rendering.

The user wants a planned restructuring before implementation. The restructuring should improve locality and leverage without doing a broad folder-by-layer rewrite, introducing fake storage adapters, or changing the public dashboard interface.

## Solution

Deepen the existing dashboard modules in narrow phases while preserving current dashboard behavior.

The solution should keep the current feature modules recognizable: run history, search, recommendations, settings, Pattern Library, Nattome POV Library, manual runs, exports, Pipeline Health, and architecture browsing remain feature-oriented modules. The improvement comes from placing repeated infrastructure and shared dashboard vocabulary behind deeper modules with small, stable interfaces.

The first priority is persistence locality. The dashboard should continue using SQLite as the only durable dashboard store, but low-level SQLite connection setup, schema initialization, dashboard database path handling, row factory defaults, and JSON serialization behavior should live in the store module. Feature modules may keep feature-specific SQL for now, but they should stop owning repeated store lifecycle and JSON fallback behavior.

The second priority is refresh orchestration. Dashboard read paths may continue refreshing derived data automatically because this is a local artifact-driven dashboard, but indexing, Scrape Quality scoring, and Pipeline Health recomputation should be routed through one explicit refresh module instead of being decided independently by each read path.

The third priority is scoring vocabulary. Nattome relevance terms, weighted engagement, freshness behavior, and score/band text should be consolidated so Scrape Quality, Search, Run History, and web-rendered summaries cannot drift.

The fourth priority is presentation cleanup. The dashboard should remove implementation details from visible UI, including the SQLite path in the topbar. The topbar should show operational status such as "Pipeline ready" and "Local workspace" rather than storage internals. The large inline theme should move behind a small theme-rendering module while preserving the self-contained local HTML approach.

The fifth priority is web request adapter cleanup. The local HTTP server should remain lightweight and should not migrate to Flask, FastAPI, or a frontend framework. It should use route/action tables and shared request helpers so POST parsing, validation error handling, redirects, and export/page dispatch are less repetitive.

The work should proceed one narrow phase at a time with characterization tests before each phase and no mixed-concern changes.

## User Stories

1. As a maintainer, I want the dashboard architecture to become less bloated, so that adding marketer-facing features does not require editing repeated low-level code across many modules.
2. As a maintainer, I want the dashboard to preserve its current public interface, so that existing tests, scripts, and imports continue working.
3. As a maintainer, I want the dashboard to keep its current feature modules, so that Run History, Search, Recommendations, Settings, Pattern Library, Nattome POV Library, and Pipeline Health remain easy to locate.
4. As a maintainer, I want targeted deepening instead of a broad folder-by-layer rewrite, so that the restructure improves locality without creating shallow abstractions.
5. As a maintainer, I want SQLite to remain the only real dashboard storage adapter, so that the codebase does not design for storage variation that does not exist.
6. As a maintainer, I want a deeper store module, so that database initialization, connection setup, path handling, row factory defaults, and JSON behavior are concentrated in one place.
7. As a maintainer, I want feature modules to stop opening SQLite connections directly from the dashboard database path, so that store lifecycle changes have one locality.
8. As a maintainer, I want feature modules to keep feature-specific SQL in the first pass, so that the refactor does not create shallow repository classes around every table.
9. As a maintainer, I want JSON loading to require explicit fallbacks, so that existing callers that expect objects, arrays, or null-like values do not regress.
10. As a maintainer, I want JSON dumping to be centralized, so that persisted dashboard-owned records remain deterministic and consistent.
11. As a maintainer, I want store connections to default to row-style access, so that repeated row factory setup disappears from feature modules.
12. As a maintainer, I want callers to keep explicit transaction commits in the first persistence phase, so that existing ordering and rollback behavior stays visible.
13. As a maintainer, I want to avoid a connection context manager in the first persistence phase, so that transaction semantics are not changed accidentally.
14. As a maintainer, I want persistence work split into a small caller phase and a heavier caller phase, so that the store interface is proven before broad migration.
15. As a maintainer, I want the first persistence phase to cover smaller direct database callers, so that early changes have a low blast radius.
16. As a maintainer, I want the second persistence phase to migrate heavier modules only after the first phase is stable, so that Run History, Search, exports, recommendations, Pattern Library, and Nattome POV Library remain protected.
17. As a maintainer, I want dashboard read paths to keep automatic refresh behavior, so that local artifact changes appear without manual refresh steps.
18. As a maintainer, I want automatic refresh routed through one refresh module, so that indexing, Scrape Quality scoring, and Pipeline Health recomputation are not scattered.
19. As a Nattome marketer, I want the dashboard to continue reflecting current Run Folder and raw scrape artifacts automatically, so that I do not need to understand internal refresh mechanics.
20. As a maintainer, I want Search, Run History, Overview, and related pages to request refresh through named scopes, so that each page gets the right derived data without owning refresh order.
21. As a maintainer, I want Scrape Quality and Nattome relevance calculations centralized, so that Overview, Search, Run History, and Recommendations show consistent signals.
22. As a Nattome marketer, I want Nattome relevance to mean the same thing wherever it appears, so that I can trust comparisons across raw videos, runs, and recommendations.
23. As a Nattome marketer, I want weighted engagement to be consistent across dashboard pages, so that a video does not appear stronger in one view and weaker in another.
24. As a maintainer, I want freshness and score band wording centralized, so that changes to scoring vocabulary are tested once.
25. As a maintainer, I want the scoring vocabulary phase to happen before visual cleanup, so that correctness risk is reduced before presentation-only bloat.
26. As a Nattome marketer, I do not want to see the SQLite path in the topbar, so that the dashboard presents operational status rather than implementation details.
27. As a Nattome marketer, I want the topbar to show simple operational context such as "Pipeline ready" and "Local workspace", so that the dashboard feels like a tool rather than a database viewer.
28. As a maintainer, I want the topbar implementation-detail cleanup included in the first persistence phase, so that visible UI matches the improved store interface.
29. As a maintainer, I want theme extraction to happen after persistence and scoring, so that presentation cleanup does not distract from correctness and locality.
30. As a maintainer, I want the dashboard theme moved behind a small theme module, so that the page layout module owns page composition rather than hundreds of lines of styling.
31. As a maintainer, I want the dashboard to keep self-contained local HTML during theme extraction, so that no static asset server is introduced prematurely.
32. As a maintainer, I want no broad visual redesign during theme extraction, so that behavior and markup remain easy to characterize.
33. As a maintainer, I want web request handling cleaned up after deeper store and scoring modules exist, so that the request adapter depends on smaller interfaces.
34. As a maintainer, I want GET and POST handling to use explicit route/action tables, so that adding a dashboard route does not require another copy-pasted conditional branch.
35. As a maintainer, I want POST body parsing, form parsing, validation error pages, and redirects handled by shared helpers, so that form actions behave consistently.
36. As a maintainer, I want the dashboard to remain on the lightweight local HTTP server, so that no framework migration adds new runtime or testing complexity.
37. As a maintainer, I want characterization tests before each phase, so that refactors preserve current behavior.
38. As a maintainer, I want each phase to be commit-sized, so that review and rollback are practical.
39. As a maintainer, I want no phase to mix persistence, scoring, CSS, and routing changes, so that regressions can be traced to one concern.
40. As a maintainer, I want tests to focus on public module behavior and UI-visible output, so that implementation details can change freely behind the module interfaces.
41. As a maintainer, I want the existing dashboard test slice to stay green after every phase, so that the refactor never outruns current behavior.
42. As a maintainer, I want the codebase to become easier for future agents to navigate, so that AI-assisted changes touch the right modules with lower regression risk.
43. As a maintainer, I want no full repository class per table, so that the codebase avoids shallow modules that add interface surface without leverage.
44. As a maintainer, I want no generic storage protocol or fake in-memory store, so that the dashboard does not create hypothetical seams with only one adapter.
45. As a maintainer, I want no public import churn, so that existing callers can keep using the dashboard package as they do today.
46. As a maintainer, I want no manual refresh requirement in this refactor, so that marketer workflows remain simple.
47. As a maintainer, I want no web framework migration, so that local dashboard serving remains simple and testable.
48. As a maintainer, I want no broad folder-by-layer rewrite, so that the current domain language remains visible in the module map.
49. As a Nattome marketer, I want dashboard behavior to remain unchanged during architecture cleanup, so that my scrape-quality workflow is not disrupted.
50. As a maintainer, I want this PRD to guide later implementation issues, so that each deepening opportunity can be picked up independently.

## Implementation Decisions

- Preserve the current public dashboard interface.
- Preserve current feature-oriented module names and responsibilities.
- Do not move existing feature modules into generic layers such as controllers, services, repositories, or views.
- Use targeted deepening of existing modules rather than a broad folder-by-layer rewrite.
- Keep SQLite as the only real dashboard storage adapter.
- Do not introduce a storage abstraction, repository base class, fake in-memory store, or adapter protocol in this phase.
- Do not create a full repository class per table.
- Deepen the store module first.
- The store module should own dashboard database initialization, connection setup, path resolution for storage access, default row access behavior, and JSON serialization helpers.
- The store connection helper should default to row-style access.
- Store JSON loading should require an explicit fallback per call site.
- Store JSON dumping should produce deterministic serialized text.
- Callers should keep explicit commit and close behavior in the first persistence phase.
- Do not introduce a connection context manager in the first persistence phase.
- Feature-specific SQL may remain inside feature modules during the first persistence phases.
- Persistence work should be split into Phase 1A and Phase 1B.
- Phase 1A should migrate the smaller direct database callers and remove the visible SQLite path from the topbar.
- Phase 1B should migrate heavier dashboard modules after Phase 1A is stable.
- The dashboard topbar should not show the SQLite path.
- The dashboard topbar should show operational status such as "Pipeline ready" and "Local workspace".
- Automatic refresh should remain part of dashboard read behavior.
- Derived refresh should be owned by one refresh module.
- The refresh module should orchestrate artifact indexing, Scrape Quality recomputation, and Pipeline Health recomputation.
- Page modules should request refresh by intent or scope instead of owning the full refresh sequence.
- Scoring vocabulary should be centralized after persistence is stable.
- The scoring module should own Nattome relevance terms, Nattome relevance computation, weighted engagement, freshness behavior, and score/band text shared by dashboard pages.
- The scoring phase should happen before web theme extraction.
- Theme extraction should happen after persistence and scoring.
- Theme extraction should keep the dashboard self-contained and Python-rendered.
- Do not introduce static asset serving during the first theme extraction.
- Web request adapter cleanup should happen after persistence and scoring, and may happen after theme extraction.
- The local HTTP server should remain the dashboard serving mechanism.
- Do not migrate to Flask, FastAPI, a JavaScript frontend framework, or another web framework as part of this refactor.
- GET and POST handling should be simplified through route/action tables and shared helpers.
- Shared POST helpers should preserve current form parsing, validation error handling, redirects, status codes, and response bodies.
- Each implementation phase should be a separate narrow change.
- Do not mix persistence, refresh, scoring, theme, and request-adapter changes in one implementation phase.
- Existing dashboard behavior should be characterized before each phase and preserved behind the new module interfaces.

## Testing Decisions

- Tests should guard current external behavior rather than redesign behavior during the refactor.
- Tests should target public module interfaces, durable dashboard records, and UI-visible output instead of private helper details.
- The existing dashboard test slice should remain green after every phase.
- Phase 0 should capture the current dashboard baseline and add missing characterization tests for the store helper behavior and the topbar not exposing the SQLite path.
- Phase 1A tests should cover store connection initialization, default row-style access, explicit JSON fallback behavior, deterministic JSON dumping, migrated smaller callers, and topbar visible text.
- Phase 1B tests should cover migrated heavy callers through existing behavior in Run History, Search, exports, Pattern Library, Nattome POV Library, recommendations, architecture browsing, Pipeline Health, and Scrape Quality.
- Refresh tests should verify that page-level refresh requests still update indexed artifacts, Scrape Quality scores, and Pipeline Health through one module.
- Scoring tests should verify that centralized Nattome relevance, weighted engagement, freshness, and band text match previous behavior.
- Scoring tests should include representative raw videos and Batch Analysis Run records.
- Theme extraction tests should verify that page rendering still includes expected layout, style markers, navigation, and page content.
- Theme extraction tests should not assert every line of CSS unless necessary for characterization.
- Web request adapter tests should verify that routes, redirects, validation errors, export responses, and page rendering remain unchanged.
- Manual run tests should verify that run trigger behavior remains distinct for scrape-only and full-pipeline runs.
- Settings tests should verify save and rollback behavior remains unchanged.
- Search tests should verify keyword and facet behavior remains unchanged.
- Export tests should verify CSV and Markdown output shape remains unchanged.
- Prior art includes the existing dashboard shell tests, manual run tests, settings/versioning coverage, global search tests, exports tests, recommendation tests, run history tests, Pattern Library tests, Nattome POV Library tests, architecture browser tests, and Pipeline Health tests.

## Out of Scope

- Implementing the refactor inside this PRD step.
- A broad folder-by-layer rewrite.
- Public import churn.
- A full repository class per table.
- Storage adapter abstraction.
- Fake in-memory dashboard store.
- Migrating away from SQLite.
- Migrating to Flask, FastAPI, a JavaScript frontend framework, or any other web framework.
- Making dashboard refresh fully manual.
- Redesigning dashboard visuals.
- Introducing static asset serving during the first theme extraction.
- Changing Scrape Quality scoring behavior beyond centralizing existing vocabulary.
- Changing marketer-facing dashboard workflows.
- Changing Batch Analysis Run, Evidence Bundle, Video Evidence Report, Run Folder, or Batch Output Set generation.
- Replacing existing Markdown, JSON, Excel, or Telegram Delivery outputs.

## Further Notes

This PRD follows the architecture decisions already agreed in the grilling session:

- Targeted deepening, not a rewrite.
- Persistence first.
- SQLite only.
- Connection and JSON locality before repository abstractions.
- Automatic refresh through one refresh module.
- Scoring consolidation before presentation cleanup.
- Theme extraction after persistence and scoring.
- Web server cleanup later, without a framework migration.
- Characterization tests before each phase.
- One narrow phase at a time.
- Preserve current public dashboard interface.
- Do not show the SQLite path in the topbar.

The implementation should use the project's domain language. Dashboard code should continue to describe Batch Analysis Runs, Run Folders, raw scraped videos, Scrape Quality, Pipeline Health, Pattern Library entries, Nattome POV entries, recommendations, and architecture docs rather than generic layers.

The intended outcome is not fewer files for its own sake. The intended outcome is deeper modules: small interfaces with more behavior behind them, better locality for future changes, and lower regression risk for the local marketer dashboard.
