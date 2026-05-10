# Update Agent Dashboard Deployment And Schema Docs

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Update the Supabase dashboard schema, data contract, and deployment documentation for agent settings and live trace events. The completed slice should make fresh installs and existing Supabase projects follow the same documented contract.

## Acceptance criteria

- [ ] Update the full Supabase dashboard schema documentation with agent settings versions and agent trace events.
- [ ] Add or update idempotent migration documentation for existing Supabase projects.
- [ ] Update the dashboard data contract to describe agent settings, trace rows, sensitive data exclusions, and artifact-reference behavior.
- [ ] Update VPS deployment docs with any required migration steps and operational notes for live tracing.
- [ ] Document that `GEMINI_API_KEY` remains environment-based and is not stored in agent settings.
- [ ] Document that full Gemini responses remain in artifacts while trace rows stay compact.
- [ ] Add or update docs tests that verify the new schema/data contract/deployment docs mention the required tables and migration path.

## Blocked by

- `docs/issues/0089-add-agent-settings-versioning-tracer.md`
- `docs/issues/0091-add-live-agent-trace-event-tracer.md`
