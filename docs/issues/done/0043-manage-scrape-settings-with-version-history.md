# Manage Scrape Settings With Version History

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build the Scrape Settings area that lets marketers directly edit production scrape settings through validated forms. Saved changes should affect the next scheduled run automatically and create a versioned configuration history with rollback support.

Risky/internal pipeline settings must remain read-only in MVP.

## Acceptance criteria

- [ ] Marketers can edit hashtags through a validated chip input that strips `#`.
- [ ] Marketers can edit keywords through a validated chip or multiline input.
- [ ] Marketers can edit competitor profiles through a validated chip input that strips `@`.
- [ ] Marketers can edit scrape scope, results per input, top N, daily selection size, minimum views, maximum age days, minimum weighted engagement rate, downloadable-video requirement, and exclusion terms.
- [ ] API keys, Apify actor ID, Gemini model, output paths, cleanup deletion settings, Telegram credentials, report schema, and scoring internals are read-only in MVP.
- [ ] Saving production settings requires a reason.
- [ ] Every save creates a config version with old value, new value, reason, user, timestamp, and active version state.
- [ ] The dashboard shows the current production config version and the version that the next scheduled run will use.
- [ ] Marketers can roll back to a previous config version without deleting history.
- [ ] Tests cover validation, normalization, required save reason, version creation, active version selection, and rollback.

## Blocked by

- `docs/issues/0037-bootstrap-local-dashboard-shell.md`
