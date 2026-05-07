# Build Candidate And Approved Pattern Library

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build the Pattern Library workflow with auto-generated Candidate Patterns and marketer-curated Approved Patterns. Patterns should represent external TikTok mechanics, not Nattome's owned interpretation.

Marketers should be able to approve, edit, archive, and version canonical pattern entries.

## Acceptance criteria

- [ ] Candidate Patterns can be generated from indexed run analysis and linked source videos.
- [ ] Candidate Patterns are clearly separate from Approved Patterns.
- [ ] Marketers can approve a Candidate Pattern into the Approved Pattern Library.
- [ ] Marketers can create and edit Approved Patterns.
- [ ] Approved Patterns support pattern name, hook type, format type, emotional trigger, source videos, why it works, Nattome adaptation notes, shoot difficulty, freshness, performance evidence, approval metadata, related POVs, avoid notes, and optional targeting fields.
- [ ] Pattern statuses include draft, approved, and archived.
- [ ] Pattern edits preserve version history with attribution and timestamps.
- [ ] Tests cover candidate generation from fixture data, approval flow, editing, archiving, source links, targeting fields, and version history.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
- `docs/issues/0042-browse-and-curate-raw-scraped-videos.md`
