# Wire Agent Config Into Gemini Runs

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Make batch analysis and Gemini reporting consume the resolved fixed-agent config. The completed slice should apply future-run agent settings to the Gemini Video Evidence Agent and Nattome Creative Strategist Agent, snapshot the resolved config into each run, and record the config source/version in the manifest.

## Acceptance criteria

- [ ] `create_run` and Gemini reporting can receive or resolve the active agent config.
- [ ] Local CLI runs use local/default agent config without requiring Supabase.
- [ ] Dashboard worker runs can pass the active Supabase agent settings into the batch run.
- [ ] The run folder stores the resolved agent config used for the run.
- [ ] The run manifest records agent config source and version.
- [ ] If the Gemini Video Evidence Agent is disabled, the full Gemini reporting chain is skipped and phases are marked clearly.
- [ ] If the Nattome Creative Strategist Agent is disabled, evidence extraction still runs and report generation is skipped.
- [ ] Invalid active config fails before any Gemini SDK call and records a visible phase failure.
- [ ] Gemini calls use configured model and supported generation config.
- [ ] Existing full Gemini responses and final reports remain stored as artifacts, not in settings.
- [ ] Add fake-client tests for enabled defaults, disabled evidence, disabled creative, config snapshotting, invalid config preflight failure, and configured generation options.

## Blocked by

- `docs/issues/0089-add-agent-settings-versioning-tracer.md`
