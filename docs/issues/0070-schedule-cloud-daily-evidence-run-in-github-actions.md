# Schedule Cloud Daily Evidence Run In GitHub Actions

Labels: needs-triage
Type: HITL

## What to build

Add a GitHub Actions workflow that runs the Python Daily Evidence Run on a daily schedule and publishes new results to Supabase.

The completed slice should put recurring worker responsibility in GitHub Actions while keeping the run cadence aligned to 09:00 Singapore time.

## Acceptance criteria

- [x] A GitHub Actions workflow can run the Daily Evidence Run manually.
- [x] The workflow is scheduled for `01:00 UTC`, equivalent to 09:00 Asia/Singapore.
- [x] The workflow installs the required Python version and project dependencies.
- [x] The workflow checks for required secrets without printing secret values.
- [x] Required GitHub secrets are documented: Apify, Gemini, optional Telegram, and Supabase variables.
- [ ] A manual workflow run publishes at least one test Daily Evidence Run to Supabase.
- [x] Workflow logs expose final output paths and cloud publication status.
- [x] The workflow does not commit generated artifacts back to the repository.

## Blocked by

- `docs/issues/0069-publish-daily-evidence-run-outputs-from-python-worker.md`

## Current status

- Added `.github/workflows/daily-evidence-run.yml` with manual dispatch and the daily `01:00 UTC` schedule.
- The workflow runs discovery, then `scripts/run_batch_analysis.py --mode daily --publish-cloud`.
- Required secrets are checked by name without printing values.
- README documents required GitHub Actions secrets and the manual verification step.

## Remaining HITL verification

- Configure the required GitHub secrets in the repository.
- Run **Daily Evidence Run Cloud Publisher** manually from GitHub Actions.
- Confirm the workflow summary shows a Run Folder, `final_outputs`, and cloud publication status `published`.
