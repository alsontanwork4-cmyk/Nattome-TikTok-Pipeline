# Rename Top-5 Operation To Daily Top-3

Labels: needs-triage
Type: AFK

## What to build

Rename current normal-operation language from Daily Top-5 Selection to Daily Top-3 Selection.

The completed slice should make the repo's current vocabulary honest before runtime behavior changes land. Historical records under `docs/issues/done/` and older PRDs should remain historical unless a new superseding ADR or current-operating note is needed.

## Decisions

- Normal operation uses a Daily Top-3 Selection.
- Up to two backfill candidates may be prepared separately, but they are not part of the canonical Daily Top-3 Selection.
- Current docs, skills, tests, filenames, labels, and workflow paths should stop teaching Top-5 as the current operating model.
- Historical issue files and old PRDs should not be rewritten as if they originally described Top-3.

## Acceptance criteria

- [ ] `CONTEXT.md` defines Daily Top-3 Selection and no longer presents Daily Top-5 Selection as current normal operation.
- [ ] README describes the normal Daily Evidence Run as Daily Top-3 Selection plus separate backfill candidates.
- [ ] Active repo-local skills use Daily Top-3 Selection language for current operation.
- [ ] Discovery handoff paths use `daily_selection_top3.json` for the canonical selection.
- [ ] Current tests assert Daily Top-3 operation rather than Daily Top-5 operation.
- [ ] Current workflow/docs do not use `daily_selection_top5.json` for new normal runs.
- [ ] Current output labels stop using "Top 5" for new production outputs.
- [ ] Historical `docs/issues/done/` files are left unchanged unless explicitly marked as superseded elsewhere.

## Out of scope

- Implementing backfill analysis behavior.
- Changing production report qualification rules.
- Rewriting historical issues and completed PRDs.

## Related follow-up

- `docs/issues/0072-enforce-evidence-qualified-production-outputs-with-backfill.md`

