# Port Legacy Dashboard Visual Theme To Jinja Shell

Labels: needs-triage
Type: AFK

## Parent

- `docs/adr/0003-supabase-first-fastapi-dashboard-rewrite.md`
- `docs/prd/vps-fastapi-dashboard-storage-migration-prd.md`

## What to build

Port the legacy dashboard's visual language into the new Jinja shell so the FastAPI dashboard feels familiar while the architecture changes underneath. Preserve the existing color theme, dense operational layout, logo treatment, navigation feel, cards, tables, buttons, and status pill styling where practical.

This is not a redesign. The completed slice should give later page slices a reusable visual foundation that looks very similar to the current dashboard.

## Acceptance criteria

- [ ] Move or adapt the legacy dashboard CSS/assets into the FastAPI asset structure.
- [ ] The base Jinja shell preserves the legacy dashboard color theme and operational control-panel feel.
- [ ] Navigation, page header, cards, tables, buttons, forms, and status pills have reusable template/CSS patterns.
- [ ] The Nattome logo remains available in the new shell if the legacy dashboard used it.
- [ ] No new color palette, marketing-style UI, or major visual redesign is introduced.
- [ ] Add a rendered HTML or screenshot smoke check for the shell/theme.
- [ ] Document that later page issues must follow the legacy visual language unless a human approves a redesign.

## Blocked by

- `docs/issues/0075-bootstrap-supabase-first-fastapi-shell.md`
