# Add Production Storage For Run Metadata

Labels: needs-triage
Type: AFK

## What to build

Implement the selected production storage path for run metadata, run outputs, settings versions, manual runs, curation, and artifact references. Large reports and videos should remain in file or object storage, with relational metadata pointing to them.

The completed slice should make hosted run history and operational decisions durable across app restarts and ready for VPS operation.

## Acceptance criteria

- [ ] Add schema for runs, run outputs, raw videos, selected videos, video curation, scrape settings versions, and manual runs as selected in the decision issue.
- [ ] Store large artifacts outside the relational database.
- [ ] Store artifact metadata such as run id, storage provider/path, size, timestamp, and checksum when available.
- [ ] FastAPI run history reads from the selected production storage path.
- [ ] Settings and curation writes use the selected production storage path.
- [ ] Add a migration or import path from current SQLite/artifact data where needed.
- [ ] Add backup and restore notes for database and artifact storage.
- [ ] Add tests for storage reads/writes and artifact metadata handling.

## Blocked by

- `docs/issues/0074-lock-fastapi-dashboard-rewrite-decisions.md`
- `docs/issues/0077-rebuild-fastapi-run-history-and-status.md`

