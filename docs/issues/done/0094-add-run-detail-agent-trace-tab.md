# Add Run Detail Agent Trace Tab

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Add run-scoped agent trace visibility to the existing run detail page. The completed slice should add a compact Agent Trace tab that shows the same trace data filtered to the selected run.

## Acceptance criteria

- [ ] Add an `Agent Trace` tab to run detail pages.
- [ ] The tab lists compact Gemini trace events filtered to the current run id.
- [ ] The tab shows agent name, candidate reference, substep, status, timestamps, elapsed duration when available, artifact references, and sanitized error summary.
- [ ] Missing trace data renders an empty state instead of failing the run detail page.
- [ ] Existing run detail tabs continue to work.
- [ ] Reuse the same trace normalization/view-model behavior as the Agents page where practical.
- [ ] Add tests for run detail tab navigation, run-scoped filtering, empty trace state, and trace row rendering.

## Blocked by

- `docs/issues/0091-add-live-agent-trace-event-tracer.md`
