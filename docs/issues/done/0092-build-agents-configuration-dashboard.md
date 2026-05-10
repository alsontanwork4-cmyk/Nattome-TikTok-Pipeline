# Build Agents Configuration Dashboard

Labels: needs-triage
Type: AFK

## Parent

- `docs/issues/0088-build-gemini-agent-management-dashboard.md`
- `docs/prd/gemini-agent-management-dashboard-prd.md`

## What to build

Add the authenticated Agents configuration page. The completed slice should add `Controls -> Agents` above Scrape Settings, let authenticated users edit the two fixed Gemini agents, preview compiled prompts, save versioned settings with a reason, and roll back prior versions.

## Acceptance criteria

- [ ] Add an authenticated `/agents` dashboard route and navigation item above Scrape Settings under Controls.
- [ ] The page manages only the Gemini Video Evidence Agent and Nattome Creative Strategist Agent.
- [ ] Provide structured prompt editing for each agent.
- [ ] Show a read-only compiled prompt preview for each agent.
- [ ] Show the fixed Nattome brand reference as metadata or preview context, but do not make it editable.
- [ ] Provide polished controls for common Gemini generation settings and advanced JSON for less common supported settings.
- [ ] Save requires a non-empty reason and records the authenticated user identity.
- [ ] Validation errors render without saving a new version.
- [ ] Version history and rollback are available from the Agents page.
- [ ] Any authenticated dashboard user can edit agent config.
- [ ] Add a small CSS/SVG mascot header that can render idle, queued, running, failed, and disabled states.
- [ ] Do not add a Gemini smoke-test button.
- [ ] Add FastAPI route/template tests for authenticated access, save, validation failure, rollback, compiled prompt preview, nav ordering, and mascot rendering.

## Blocked by

- `docs/issues/0089-add-agent-settings-versioning-tracer.md`
