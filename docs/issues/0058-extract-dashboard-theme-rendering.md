# Extract Dashboard Theme Rendering

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0052-deepen-dashboard-codebase-architecture.md`

## What to build

Move the large inline dashboard theme out of the page layout module and behind a small Python theme-rendering module. Preserve the current self-contained local HTML response and avoid introducing static asset serving or a broader visual redesign.

## Acceptance criteria

- [ ] Dashboard theme styles are rendered from a dedicated theme module.
- [ ] The page layout module focuses on page composition rather than owning the full theme body.
- [ ] The dashboard still returns self-contained local HTML.
- [ ] No static asset server is introduced.
- [ ] No broad visual redesign is performed.
- [ ] Rendered pages still include expected navigation, layout, style markers, and page content.
- [ ] Tests cover page rendering after theme extraction without overfitting to every CSS line.
- [ ] Existing dashboard tests remain green.

## Blocked by

- `docs/issues/0054-localize-store-access-for-small-dashboard-callers.md`
- `docs/issues/0057-centralize-nattome-scoring-vocabulary.md`
