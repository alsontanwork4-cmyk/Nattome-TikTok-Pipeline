# Add Live Agent Trace Event Tracer

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Add compact live trace events for Gemini agent execution. The completed slice should write structured trace rows directly to Supabase while a run is executing, so the dashboard can show live agent progress before post-run artifact upload completes.

## Acceptance criteria

- [ ] Add Supabase schema support for compact agent trace events.
- [ ] Add an idempotent existing-project migration for the trace table/indexes.
- [ ] Add dashboard data client methods for inserting/upserting trace events and listing recent or run-scoped trace events.
- [ ] Trace events include run id, agent name, candidate reference, substep, status, start/end timestamps, config source/version, artifact references, uploaded Gemini file metadata, response usage metadata when available, and sanitized error summary.
- [ ] Write trace events during Gemini substeps: uploading video, waiting for file active, generating evidence, generating creative strategy, writing artifacts, completed, skipped, and failed.
- [ ] Compute completed durations from start/end timestamps and leave running events open until finished.
- [ ] Do not store API keys, raw environment values, full local filesystem paths, or full Gemini response text in trace rows.
- [ ] Continue storing full Gemini responses and reports in artifacts.
- [ ] Missing credentials, invalid config, unavailable videos, skipped artifacts, and Gemini errors produce honest trace statuses.
- [ ] Add tests for trace event sequencing, sanitization, run-scoped listing, recent listing, skipped events, and failed events.

## Blocked by

- `docs/issues/0089-add-agent-settings-versioning-tracer.md`
- `docs/issues/0090-wire-agent-config-into-gemini-runs.md`
