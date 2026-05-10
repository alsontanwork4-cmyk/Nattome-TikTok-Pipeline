# Dashboard Architecture Contract Verification

Date: 2026-05-07

Parent PRD: `docs/prd/dashboard-codebase-architecture-deepening-prd.md`

## Scope

This document records the final verification pass for issue `0060`. It traces the dashboard architecture PRD constraints to the completed implementation slices and executable tests. The verification is intentionally narrow: it confirms the architecture contract after issues `0053` through `0059` without introducing another dashboard behavior change.

## Completed Slices

- `0053` characterized dashboard architecture behavior, public imports, topbar output, store initialization, health checks, and unknown-route behavior.
- `0054` localized smaller dashboard store callers behind `dashboard.store`.
- `0055` localized heavier feature modules behind `connect_dashboard_store` while keeping feature-specific SQL in feature modules.
- `0056` centralized derived dashboard refresh in `dashboard.refresh`.
- `0057` centralized Nattome scoring vocabulary in `dashboard.scoring`.
- `0058` extracted inline theme rendering into `dashboard.web_theme`.
- `0059` simplified the lightweight dashboard request adapter with GET export and POST form action dispatch tables.
- `0060` adds this contract verification document and executable architecture checks.

## Contract Results

| PRD contract | Verification result |
| --- | --- |
| Public dashboard imports remain stable | Covered by `test_public_dashboard_web_imports_remain_usable`, which verifies `dashboard.web.__all__` and import identities. |
| Current feature-oriented dashboard modules remain recognizable | Covered by `test_dashboard_architecture_contract_has_no_prohibited_abstractions`, which verifies key feature modules such as Run History, Search, Recommendations, Settings, Nattome POV Library, exports, and architecture browsing still exist. |
| No broad folder-by-layer rewrite | Covered by `test_dashboard_architecture_contract_has_no_prohibited_abstractions`, which rejects generic dashboard `controllers`, `repositories`, `services`, and `adapters` folders. |
| No full repository class per table | Covered by source checks that reject `Repository` and `class DashboardStore` patterns. Feature-specific SQL remains in feature modules where useful. |
| No storage adapter abstraction, fake in-memory store, or generic store protocol | Covered by source checks rejecting `Protocol` and `class InMemory` patterns in dashboard modules. |
| SQLite remains the only dashboard store | Covered by source checks that allow `sqlite3.connect` only in `dashboard.store`, where `initialize_dashboard_store` and `connect_dashboard_store` own the SQLite connection lifecycle. |
| Automatic refresh remains part of dashboard read paths | Covered by `test_dashboard_read_paths_keep_automatic_refresh_contract`, plus behavior tests around Overview, Search, Run History, Recommendations, and architecture browsing. |
| The SQLite path is not visible in the dashboard topbar | Covered by `test_topbar_preserves_visible_brand_and_operational_status`. The topbar shows operational text such as "Pipeline ready" and "Local workspace". |
| The local HTTP server remains the serving mechanism | Covered by `test_dashboard_serving_contract_stays_lightweight_http_server`, which verifies `BaseHTTPRequestHandler` and `ThreadingHTTPServer`. |
| No web framework migration occurred | Covered by `test_dashboard_serving_contract_stays_lightweight_http_server`, which rejects Flask, FastAPI, Django, Starlette, and Uvicorn imports in the dashboard web server. |
| The dashboard test slice remains green | Verified with `python -m pytest tests -k dashboard`. |
| PRD acceptance criteria are traceable to completed implementation or explicitly deferred follow-up work | This document is the traceability artifact and is checked by `test_architecture_contract_verification_is_traceable_to_prd`. |

## Deferred Follow-Up Work

Deferred follow-up work: None

The architecture deepening PRD constraints have corresponding implementation slices and executable regression checks. Future dashboard features can build on the current feature-oriented module map without adding storage adapters, repository-per-table classes, generic layers, or a web framework migration.
