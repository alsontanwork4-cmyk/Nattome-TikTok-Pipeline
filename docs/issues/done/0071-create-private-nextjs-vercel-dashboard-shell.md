# Create Private Next.js Vercel Dashboard Shell

Labels: needs-triage
Type: AFK

## What to build

Create the first Next.js TypeScript dashboard shell for Vercel under a separate web app while leaving the current Python dashboard package intact.

The completed slice should establish private access, Supabase connectivity, and a minimal read-only dashboard frame that can later display Daily Evidence Run data.

## Acceptance criteria

- [x] A new Next.js TypeScript app is added without replacing the existing Python dashboard.
- [x] The app is structured for Vercel deployment from the new web app location.
- [x] Supabase Auth protects dashboard routes from anonymous access.
- [x] Environment variable documentation covers Vercel-side Supabase configuration.
- [x] A minimal authenticated dashboard page renders successfully.
- [x] The dashboard data-access layer can request the latest run through a small interface.
- [x] Tests or local checks verify unauthenticated users cannot access the dashboard page.
- [x] No Python pipeline behavior changes are included in this slice.

## Blocked by

- `docs/issues/0068-add-supabase-cloud-run-publication-tracer-bullet.md`

## Completion notes

- Added `web/vercel-dashboard/` as a separate Next.js TypeScript app for Vercel.
- Added Supabase SSR middleware and server-side auth helpers so anonymous dashboard access redirects to `/login`.
- Added a minimal authenticated dashboard shell and a small `DailyEvidenceRunRepository.getLatestRun()` interface over `daily_evidence_runs`.
- Documented Vercel-side Supabase environment variables in `README.md` and `.env.example`.
- Verified the app with TypeScript, a production build, Python contract tests, and a local anonymous redirect check.
