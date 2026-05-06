# Add OCR Evidence Capture

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Run OCR over Hybrid Timeline frames and produce timestamped OCR evidence. PaddleOCR should be the primary OCR path, with a fallback strategy for environments where the primary engine is unavailable.

## Acceptance Criteria

- [ ] OCR runs against extracted timeline frames.
- [ ] OCR output is timestamped and linked back to source frame paths.
- [ ] OCR output is stored as structured JSON in each Evidence Bundle.
- [ ] OCR summary output is available for report generation.
- [ ] The OCR path supports English, Malay, Simplified Chinese, Traditional Chinese, and mixed-language text where feasible.
- [ ] Missing OCR tooling produces a clear setup error.

## Blocked By

- `0004-extract-hybrid-timeline-frames.md`
