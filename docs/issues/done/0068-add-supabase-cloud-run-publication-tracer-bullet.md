# Add Supabase Cloud Run Publication Tracer Bullet

Labels: needs-triage
Type: AFK

## What to build

Add the first end-to-end publication path from a completed Daily Evidence Run into Supabase using a compact cloud schema and a testable publication interface.

The completed slice should prove that run metadata and artifact references can be written to cloud-facing adapters without requiring the full scheduled worker or Vercel dashboard to exist yet.

## Acceptance criteria

- [x] A compact cloud run model represents Daily Evidence Run status, timestamps, report date, summary fields, and publication errors.
- [x] A compact artifact model represents Run Folder outputs, Daily Output Set files, artifact type, storage path, filename, and content type.
- [x] A publication interface can create or update a cloud run record.
- [x] A publication interface can publish artifact records for markdown, JSON, spreadsheet, raw scrape, daily selection, and batch-analysis outputs.
- [x] Tests verify successful publication with fake Supabase clients or isolated adapters.
- [x] Tests verify failed artifact publication does not mark the run as fully successful.
- [x] The implementation does not require importing historical local runs.

## Completion notes

- Added `batch_analysis.cloud_publication` with compact `CloudRunRecord` and `CloudArtifactRecord` models.
- Added `SupabasePublicationAdapter` using the Supabase-style `client.table(...).upsert(...).execute()` boundary without adding a runtime dependency.
- Added `build_cloud_run_record` and `artifact_record_from_path` builders for new-run publication paths.
- Kept the slice limited to explicit run/artifact inputs; it does not scan or import historical local runs.
- Added fake-client tests in `tests/test_cloud_publication.py`.

## Blocked by

None - can start immediately.
