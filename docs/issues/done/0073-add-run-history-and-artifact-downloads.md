# Add Run History And Artifact Downloads

Labels: needs-triage
Type: AFK

## What to build

Add read-only run history and artifact download access to the private Vercel dashboard.

The completed slice should let authenticated users browse new cloud-published Daily Evidence Runs and retrieve the generated markdown, JSON, spreadsheet, and supporting artifact files.

## Acceptance criteria

- [x] The dashboard shows a run history list for cloud-published Daily Evidence Runs.
- [x] Users can open a run detail view from the history list.
- [x] The run detail view shows status, timestamps, summary fields, and associated artifacts.
- [x] Artifact download links are generated through the approved Supabase access pattern.
- [x] Download links do not expose secrets or service-role credentials.
- [x] The run history handles failed, incomplete, and successful publication states.
- [x] Tests or local checks cover run list, run detail, successful downloads, and missing artifact states.

## Blocked by

- `docs/issues/0072-show-latest-daily-evidence-run-in-vercel-dashboard.md`

## Completion notes

- Added run history loading for recent cloud Daily Evidence Run records across publication states.
- Added authenticated run detail pages at `/runs/[runId]`.
- Reused the latest-run view model for detail pages so summary fields and missing artifacts render consistently.
- Converted Supabase artifact links to public storage download URLs without service-role credentials.
- Added Node tests for run history, run detail, download URLs, and missing artifact states.
