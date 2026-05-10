# Rebuild FastAPI Settings And Curation Flows

Labels: needs-triage
Type: AFK

## What to build

Rebuild scrape settings and video curation flows in the FastAPI dashboard. The slice should let the owner view settings, save a new version, roll back settings, and persist video curation decisions through authenticated routes.

The completed slice should preserve the operational value of settings and curation while moving the web behavior into the new FastAPI architecture.

## Acceptance criteria

- [ ] Implement `GET /scrape-settings` in the FastAPI app.
- [ ] Implement authenticated settings save route.
- [ ] Implement authenticated settings rollback route.
- [ ] Implement authenticated video curation save route.
- [ ] Validate form data server-side and show clear errors.
- [ ] Settings changes are versioned and rollbackable.
- [ ] Curation labels and notes persist.
- [ ] Add tests for settings view, save, rollback, validation errors, and curation persistence.

## Blocked by

- `docs/issues/0075-bootstrap-fastapi-dashboard-health-slice.md`
- `docs/issues/0078-add-authenticated-manual-run-trigger.md`

