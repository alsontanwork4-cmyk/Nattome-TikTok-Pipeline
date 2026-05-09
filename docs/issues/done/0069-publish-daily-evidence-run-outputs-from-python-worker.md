# Publish Daily Evidence Run Outputs From Python Worker

Labels: needs-triage
Type: AFK

## What to build

Wire the Python Daily Evidence Run workflow to publish new completed runs to Supabase after local output generation succeeds.

The completed slice should keep the evidence-first local pipeline behavior intact while adding a cloud publication step for new Run Folders and Daily Output Sets.

## Acceptance criteria

- [x] A completed Daily Evidence Run can publish its run metadata to the cloud publication interface.
- [x] The raw scrape, Daily Top-5 Selection, final markdown reports, structured JSON, spreadsheet summary, and relevant batch-analysis artifacts are uploaded or registered.
- [x] Publication failure is reported clearly without pretending the cloud run is complete.
- [x] Local output generation remains usable when cloud publication is disabled.
- [x] Required cloud environment variables are documented and checked without printing secret values.
- [x] Tests cover enabled publication, disabled publication, and publication failure behavior.
- [x] Existing local dashboard behavior is not removed or replaced.

## Blocked by

- `docs/issues/0068-add-supabase-cloud-run-publication-tracer-bullet.md`

## Completion notes

- Added `--publish-cloud` to the Python worker while keeping publication disabled by default.
- Registered completed Daily Evidence Run metadata and artifact records through the cloud publication interface after local output generation succeeds.
- Added a standard-library Supabase REST client boundary so the worker can publish without a third-party runtime dependency.
- Wrote `logs/cloud_publication.json` for publication success or failure, and raised a clear cloud publication error without deleting local outputs.
- Documented `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` requirements without exposing secret values.
