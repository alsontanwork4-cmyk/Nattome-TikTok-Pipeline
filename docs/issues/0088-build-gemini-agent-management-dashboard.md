# Build Gemini Agent Management Dashboard

Labels: needs-triage
Type: HITL

## Parent

- `docs/prd/gemini-agent-management-dashboard-prd.md`
- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`

## What to build

Add an authenticated Agents dashboard section for managing and tracing the two fixed Gemini agents used by the Nattome TikTok Source Video Pipeline: the Gemini Video Evidence Agent and the Nattome Creative Strategist Agent.

The completed slice should let users edit versioned future-run agent configuration, inspect compiled prompts, see live per-agent execution status with elapsed running time, review compact trace history, and open run-specific agent traces from run detail pages.

## Acceptance criteria

- [ ] Add `Controls -> Agents` above Scrape Settings.
- [ ] Manage only the Gemini Video Evidence Agent and Nattome Creative Strategist Agent.
- [ ] Provide structured prompt editing and compiled prompt preview for each agent.
- [ ] Provide polished controls for common Gemini SDK generation settings and advanced JSON for less common supported settings.
- [ ] Validate required prompt sections, model names, numeric ranges, advanced JSON object shape, supported Gemini config keys, and polished-field conflicts before saving.
- [ ] Keep Gemini API keys out of dashboard-managed config.
- [ ] Store production agent settings in a Supabase versioned active-settings table with reason, rollback, creator identity, and timestamps.
- [ ] Provide local CLI fallback config plus built-in defaults, normalized through the same validation layer.
- [ ] Snapshot the resolved agent config and config source/version into each run.
- [ ] Apply config changes only to future runs.
- [ ] If the Evidence Agent is disabled, skip the full Gemini reporting chain.
- [ ] If the Creative Strategist Agent is disabled, still run evidence extraction and skip report generation.
- [ ] Write compact structured live trace events directly to Supabase during agent execution.
- [ ] Trace events include agent, candidate reference, substep, status, start/end timestamps, config version/source, artifact references, uploaded Gemini file metadata, usage metadata when available, and sanitized error summaries.
- [ ] Do not store API keys, raw environment values, full local filesystem paths, or full Gemini response text in trace rows.
- [ ] Show one live status row per agent with enabled state, model, config version, current state, current candidate, elapsed running time, latest error, and last completed timestamp.
- [ ] Add polling refresh for live status and traces; do not add websockets or SSE.
- [ ] Add a small CSS/SVG mascot at the top of the Agents page reflecting overall status.
- [ ] Add an Agent Trace tab to run detail pages.
- [ ] Update full Supabase schema docs and add an idempotent migration for existing deployments.
- [ ] Add tests for config validation, settings versioning, prompt compilation, disabled-agent behavior, trace event writes, Agents page routes, and run-detail trace rendering.

## Blocked by

None - product and architecture decisions are captured in the parent PRD.
