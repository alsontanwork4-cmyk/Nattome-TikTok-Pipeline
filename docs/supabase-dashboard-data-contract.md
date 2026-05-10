# Supabase Dashboard Data Contract

The FastAPI dashboard uses Supabase Postgres for metadata and Supabase Storage for large artifacts. This contract is intentionally compact and direct: route slices should call the small dashboard Supabase boundary instead of creating repository-per-table layers.

Required tables:

- `runs`: run identity, status, type, timing, trigger/audit identity, counts, report date, summary, and concise error summary.
- `run_outputs`: artifact metadata for Supabase Storage objects.
- `raw_videos`: raw TikTok candidate metadata for browsing and exports.
- `selected_videos`: selected candidate membership and evidence status for a run.
- `scrape_settings_versions`: versioned settings payloads, reasons, active version, rollback source, and creator identity.
- `agent_settings_versions`: versioned Gemini Video Evidence Agent and Nattome Creative Strategist Agent settings, including enabled state, structured prompt sections, model name, polished generation controls, advanced Gemini generation config, save reason, active version, rollback source, and creator identity. GEMINI_API_KEY remains environment-based and must not be stored in this table.
- `agent_trace_events`: compact live Gemini agent trace rows with run id, agent, candidate reference, substep, status, timestamps, config source/version, artifact references, uploaded Gemini file metadata, usage metadata, and sanitized error summary. Trace rows must not store API keys, raw environment values, full local filesystem paths, or full Gemini response text.
- `manual_runs`: queued/running/finished manual run requests claimed by the worker, including trigger identity, requested/claimed/finished timestamps, expected output metadata, and concise failure summaries.

Manual run statuses use the compact worker contract: `queued`, `running`, `succeeded`, `failed`, and `canceled`. FastAPI only inserts queued manual run records and matching queued `runs` rows; the worker claims queued records, updates visible run status, and publishes artifact metadata after Supabase Storage upload.

Artifact metadata fields live in `run_outputs`: `run_id`, `artifact_type`, `bucket`, `object_path`, `filename`, `content_type`, `size_bytes`, `checksum`, and `created_at`. Large files stay in Supabase Storage; Postgres stores only metadata and lookup fields.

Agent trace artifact references are relative object paths or compact filenames that point back to `run_outputs`/Storage objects. Full Gemini responses remain Supabase Storage artifacts; trace rows keep only compact status, timing, usage metadata, uploaded-file metadata, artifact references, and sanitized error summaries.

The code-level source of truth is `dashboard/supabase_client.py`, which exposes `DASHBOARD_TABLE_CONTRACT`, `ArtifactMetadata`, and `DashboardSupabaseClient`.

Scrape settings version writes use the `save_scrape_settings_version` Supabase RPC so the active-version flip and insert happen in one transaction. Agent settings use the matching `save_agent_settings_version` RPC. The schema enforces one active version per settings table with partial unique indexes.

Fresh Supabase installs should apply `docs/supabase-dashboard-schema.sql`. Existing Supabase projects should apply the idempotent migrations in `docs/migrations/20260510_agent_settings_versions.sql` and `docs/migrations/20260510_agent_trace_events.sql`; both use `create table if not exists`, `create index if not exists`, and `create or replace function` where applicable.
