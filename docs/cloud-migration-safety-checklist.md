# Cloud Migration Safety Checklist

This checklist protects local Daily Evidence Run history before cloud migration work changes the project workflow.

## Protected Local Inputs

- `data/` - raw scrapes, Daily Output Sets, daily handoffs, and dashboard-owned local state files that are not SQLite databases.
- `outputs/` - marketer-facing reports, workbooks, run summaries, and path indexes.
- `runs/` - Run Folders, audit artifacts, logs, evidence snapshots, and source-video evidence bundles.
- `.env` - local credential file.

## Backup Record

- Archive: `local-backups/nattome-local-evidence-backup-20260509T021437Z.zip`
- Receipt: `local-backups/nattome-local-evidence-backup-20260509T021437Z.md`
- Created at: `2026-05-09T02:14:37Z`
- Storage policy: keep the archive and receipt local; do not commit them.

## Migration Safety

- Old local history is backed up but not imported into cloud dashboard v1.
- Cloud dashboard v1 starts from newly published run records only.
- `.env`, dashboard SQLite files, generated run artifacts, and local backup archives stay ignored by git.
- Before migration commits, run `git status --short` and confirm no secrets, SQLite files, generated artifact folders, or local backup archives are staged.
