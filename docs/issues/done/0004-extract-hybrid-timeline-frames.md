# Extract Hybrid Timeline Frames

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Extract Hybrid Timeline frames from each downloaded video using FFmpeg. The first implementation should create one-second baseline samples, extra first-three-second hook samples, and a timeline JSON structure ready for OCR and visual notes.

## Acceptance Criteria

- [ ] The pipeline extracts frames from each downloaded video.
- [ ] The pipeline creates at least one frame per second by default.
- [ ] The first three seconds receive extra hook-focused samples.
- [ ] Frame files are stored as Evidence Artifacts in each per-video folder.
- [ ] Timeline JSON records timestamp, frame path, and sampling reason.
- [ ] The implementation leaves extension points for text-change and scene-change samples.

## Blocked By

- `0003-download-video-evidence-bundles.md`
