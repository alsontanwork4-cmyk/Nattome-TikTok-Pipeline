# Document Cloud Operations And Deferred Control Room Scope

Labels: needs-triage
Type: AFK

## What to build

Document how the cloud Daily Evidence Run system operates across GitHub Actions, Supabase, and Vercel, and make the deferred control-room scope explicit.

The completed slice should let a future operator understand how new runs are produced, where outputs live, how the Vercel dashboard reads them, and what remains local or out of scope for v1.

## Acceptance criteria

- [x] Documentation explains that Python remains the worker for Apify discovery, Gemini evidence analysis, and Daily Output Set generation.
- [x] Documentation explains that Vercel hosts the private read-only Next.js dashboard.
- [x] Documentation explains that Supabase Postgres stores compact run metadata and Supabase Storage stores generated artifacts.
- [x] Documentation explains that GitHub Actions runs the daily worker at 09:00 Singapore time.
- [x] Documentation states that cloud v1 shows new runs only and does not import historical local runs.
- [x] Documentation points operators to the local backup process for old data preservation.
- [x] Documentation lists required GitHub Actions and Vercel environment variables without secret values.
- [x] Documentation explicitly defers manual run triggers, scrape setting edits, curation labels, rollback controls, and full control-room behavior.

## Blocked by

- `docs/issues/0070-schedule-cloud-daily-evidence-run-in-github-actions.md`
- `docs/issues/0073-add-run-history-and-artifact-downloads.md`

## Completion notes

- Added `docs/cloud-operations.md` as the operator guide for the cloud Daily Evidence Run v1 system.
- Documented that Python remains the worker, GitHub Actions schedules it at 09:00 Singapore time, Supabase stores metadata/artifacts, and Vercel hosts the private read-only dashboard.
- Documented the new-runs-only cloud v1 policy and linked operators to the local backup checklist.
- Listed required GitHub Actions and Vercel configuration names without secret values.
- Made deferred cloud control-room scope explicit.
