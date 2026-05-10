# Add Agent Settings Versioning Tracer

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Add the first end-to-end tracer for fixed Gemini agent settings. The completed slice should define the versioned settings contract, validate the two fixed agent configs, support Supabase active-version reads/writes/rollback, and provide local/default fallback config for non-Supabase runs.

## Acceptance criteria

- [ ] Define a normalized config shape for the Gemini Video Evidence Agent and Nattome Creative Strategist Agent.
- [ ] Include enabled state, structured prompt sections, model name, polished Gemini generation controls, and advanced JSON config per agent.
- [ ] Validate required prompt sections, model names, numeric ranges, advanced JSON object shape, supported Gemini generation config keys, and polished-field conflicts.
- [ ] Keep `GEMINI_API_KEY` out of dashboard-managed agent config.
- [ ] Add Supabase schema support for versioned active agent settings with save reason, rollback source, creator/updater identity, and timestamps.
- [ ] Add an idempotent existing-project migration for the new settings table/function.
- [ ] Add dashboard data client methods for listing, saving, and rolling back agent settings versions.
- [ ] Add local JSON fallback config loading for CLI runs when Supabase is unavailable.
- [ ] Use built-in defaults when no active Supabase/local config exists.
- [ ] Add tests for defaults, local fallback, Supabase version mapping, validation failures, rollback, and polished-field conflict rejection.

## Blocked by

None - can start immediately
