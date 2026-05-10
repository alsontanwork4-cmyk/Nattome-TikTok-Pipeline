# Supabase Dashboard Data Contract

The FastAPI dashboard uses Supabase Postgres for metadata and Supabase Storage for large artifacts. This contract is intentionally compact and direct: route slices should call the small dashboard Supabase boundary instead of creating repository-per-table layers.

Required tables:

- `runs`: run identity, status, type, timing, trigger/audit identity, counts, report date, summary, and concise error summary.
- `run_outputs`: artifact metadata for Supabase Storage objects.
- `raw_videos`: raw TikTok candidate metadata for browsing and exports.
- `selected_videos`: selected candidate membership and evidence status for a run.
- `video_curation`: labels, notes, exclusion reason, and Supabase Auth audit identity.
- `scrape_settings_versions`: versioned settings payloads, reasons, active version, rollback source, and creator identity.
- `manual_runs`: queued/running/finished manual run requests claimed by the worker.

Artifact metadata fields live in `run_outputs`: `run_id`, `artifact_type`, `bucket`, `object_path`, `filename`, `content_type`, `size_bytes`, `checksum`, and `created_at`. Large files stay in Supabase Storage; Postgres stores only metadata and lookup fields.

The code-level source of truth is `dashboard/supabase_client.py`, which exposes `DASHBOARD_TABLE_CONTRACT`, `ArtifactMetadata`, and `DashboardSupabaseClient`.
