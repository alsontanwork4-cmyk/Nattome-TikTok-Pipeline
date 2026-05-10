# Lock FastAPI Dashboard Rewrite Decisions

Labels: needs-triage
Type: HITL

## What to build

Make the human architectural decisions needed before the VPS FastAPI dashboard rewrite starts. This issue should turn the PRD's open questions into explicit project decisions so later AFK slices can implement without guessing.

The completed slice should define the production storage choice, authentication approach, template strategy, batch execution shape, and the keep/adapt/rewrite/delete classification for existing dashboard modules.

## Acceptance criteria

- [ ] Production storage is selected: Supabase Postgres, local VPS Postgres, or another explicit choice.
- [ ] Large artifact storage is selected: VPS disk, Supabase Storage, or another explicit choice.
- [ ] Authentication approach is selected: simple owner password/session, Supabase Auth, or another explicit choice.
- [ ] Rendering approach is selected: server-rendered templates, Python-rendered HTML, or a documented hybrid.
- [ ] Batch execution approach is selected: FastAPI background task, separate worker process, `systemd` job, or another explicit choice.
- [ ] Existing dashboard modules are classified as keep, adapt, rewrite, or delete.
- [ ] The final route map for the FastAPI dashboard is documented.
- [ ] The final compact module map is documented.
- [ ] Decisions are recorded in the PRD, an ADR, or a current architecture note.

## Blocked by

None - can start immediately

