# Add Authenticated Manual Run Trigger

Labels: needs-triage
Type: AFK

## What to build

Add the authenticated FastAPI flow for triggering a full pipeline run from the hosted dashboard. The route should start work safely, record status, prevent duplicate active runs, and return a useful browser response.

The completed slice should make the hosted dashboard a real control surface while avoiding duplicate long-running batch jobs.

## Acceptance criteria

- [ ] Add production authentication for mutating dashboard routes.
- [ ] Implement an authenticated manual full-pipeline trigger route.
- [ ] Record trigger user, trigger time, run type, status, and output metadata.
- [ ] Prevent duplicate active full-pipeline runs.
- [ ] Long-running execution does not block the web request until completion.
- [ ] Trigger failures produce a visible, actionable error.
- [ ] Add tests for unauthenticated trigger rejection.
- [ ] Add tests for successful trigger, failed trigger, and duplicate active run prevention.

## Blocked by

- `docs/issues/0077-rebuild-fastapi-run-history-and-status.md`

