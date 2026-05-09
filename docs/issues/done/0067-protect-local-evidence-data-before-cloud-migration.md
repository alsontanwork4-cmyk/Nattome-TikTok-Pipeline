# Protect Local Evidence Data Before Cloud Migration

Labels: needs-triage
Type: HITL

## What to build

Create and verify a local backup process before any cloud migration work changes the project workflow.

The completed slice should make it clear which local Daily Evidence Run data, Run Folders, Daily Output Sets, dashboard state, and credentials are protected, and should prevent generated artifacts or secrets from being accidentally committed during migration.

## Acceptance criteria

- [x] A timestamped local backup archive is created for `data/`, `outputs/`, `runs/`, and `.env`.
- [x] The backup archive can be opened and contains the expected top-level folders and credential file.
- [x] Documentation records where the backup archive is stored and when it was created.
- [x] Git ignore rules continue to exclude `.env`, dashboard SQLite files, generated run artifacts, and local backup archives.
- [x] A migration safety checklist documents that old local history is backed up but not imported into the cloud dashboard v1.
- [x] `git status --short` confirms no secrets, SQLite files, or generated artifact folders are staged for commit.

## Completion notes

- Added `batch_analysis.local_backup.create_local_evidence_backup` and `scripts/create_local_backup.py`.
- Created local archive `local-backups/nattome-local-evidence-backup-20260509T021437Z.zip`.
- Created matching local receipt `local-backups/nattome-local-evidence-backup-20260509T021437Z.md`.
- Recorded the backup path and creation time in `docs/cloud-migration-safety-checklist.md`.
- Added tests in `tests/test_local_backup.py`.
- Restored full-suite verification by keeping dashboard settings compatibility and isolating existing subprocess tests from local `.env` and repo-level `outputs/`.
- Verified `python -m unittest discover -s tests` passes with 123 tests.

## Blocked by

None - can start immediately.
