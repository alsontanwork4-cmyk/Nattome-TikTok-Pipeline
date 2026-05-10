# Build Live Runs And Trace History UI

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Add live agent monitoring and trace history to the Agents page. The completed slice should show one operational status row per fixed Gemini agent, compute elapsed time while an agent is running, poll for updates, and show compact trace history across runs.

## Acceptance criteria

- [ ] The Agents page shows one live status row for each fixed Gemini agent.
- [ ] Each row shows enabled state, active model, config version, current state, current candidate, elapsed running time, latest error summary, and last completed timestamp.
- [ ] Current state supports idle, queued, running, failed, disabled, and last succeeded.
- [ ] Running elapsed time is computed from trace start timestamp until a finished timestamp exists.
- [ ] Trace history shows recent compact trace events with substep, status, run id, candidate reference, timestamps, artifact references, and sanitized error summary.
- [ ] The page has a manual refresh path and auto-refreshes every 5-10 seconds while any agent is running.
- [ ] Do not add websockets or server-sent events.
- [ ] Mascot state reflects overall status using priority failed, running, queued, disabled, idle.
- [ ] Failed mascot state clears when a newer event for the same agent starts or succeeds.
- [ ] Latest error summaries remain visible in rows/history after mascot state changes.
- [ ] Add route/view-model/template tests for status derivation, elapsed time, polling marker, trace history rendering, and mascot state priority.

## Blocked by

- `docs/issues/0091-add-live-agent-trace-event-tracer.md`
- `docs/issues/0092-build-agents-configuration-dashboard.md`
