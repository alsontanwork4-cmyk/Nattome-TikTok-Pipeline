# Create Batch Analysis Run Skeleton

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Create the first runnable Batch Analysis Run skeleton. It should create a timestamped Run Folder, record batch metadata, expose the basic run modes, and fail clearly when required setup is missing.

## Acceptance Criteria

- [ ] A user can start a Batch Analysis Run from the workspace.
- [ ] The run creates one Run Folder using the agreed folder structure.
- [ ] The run records batch metadata, including run timestamp, mode, requested batch size, and configuration.
- [ ] Missing required setup is reported clearly without fabricating outputs.
- [ ] The skeleton can run without video OCR or transcription being implemented yet.

## Blocked By

None - can start immediately.
