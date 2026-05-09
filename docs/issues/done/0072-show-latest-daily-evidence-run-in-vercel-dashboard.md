# Show Latest Daily Evidence Run In Vercel Dashboard

Labels: needs-triage
Type: AFK

## What to build

Display the latest published Daily Evidence Run in the private Vercel dashboard.

The completed slice should let an authenticated marketer open the dashboard and see the newest run summary, publication status, and key Daily Output Set links.

## Acceptance criteria

- [x] The dashboard loads the latest cloud-published Daily Evidence Run.
- [x] The dashboard shows run status, run timestamp, report date, and high-level summary fields.
- [x] The dashboard links to the Cross-Video Pattern Summary when available.
- [x] The dashboard links to final markdown, structured JSON, spreadsheet, raw scrape, and Daily Top-5 Selection artifacts when available.
- [x] Missing artifacts are shown as unavailable rather than causing the page to fail.
- [x] Empty-state copy appears when no cloud runs have been published yet.
- [x] Tests or local checks cover latest run, missing artifact, and no-run states.

## Blocked by

- `docs/issues/0069-publish-daily-evidence-run-outputs-from-python-worker.md`
- `docs/issues/0071-create-private-nextjs-vercel-dashboard-shell.md`

## Completion notes

- Extended the Vercel dashboard repository to load the newest `published` Daily Evidence Run plus its artifact rows.
- Added a typed view model for latest-run, missing-artifact, and no-run states.
- Rendered run status, run timestamp, report date, summary fields, and Daily Output Set links in the authenticated dashboard.
- Added Node tests for latest run loading, artifact mapping, missing artifact availability, and empty-state behavior.
