# Generate Structured JSON And Spreadsheet Summary

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Produce the required machine-readable Structured JSON Output and marketing-facing Spreadsheet Summary Output for each Batch Analysis Run.

## Acceptance Criteria

- [ ] Each Batch Analysis Run produces Structured JSON Output.
- [ ] Structured JSON preserves batch metadata, selection decisions, Evidence Bundle indexes, Hybrid Timeline, OCR, transcript, audio analysis, virality analysis, claim safety review, quality score, manual review flag, Shootable Angles, and Nattome Priority Score.
- [ ] Each Batch Analysis Run produces a spreadsheet summary.
- [ ] The spreadsheet has one row per analyzed video.
- [ ] The spreadsheet includes link, topic, hook type, format, emotional trigger, avatar, product fit, priority score, evidence quality, and recommended angle.
- [ ] Markdown, JSON, and spreadsheet outputs are written into the Run Folder.

## Blocked By

- `0010-generate-per-video-evidence-reports.md`
- `0011-generate-cross-video-pattern-summary-and-priority-scores.md`
