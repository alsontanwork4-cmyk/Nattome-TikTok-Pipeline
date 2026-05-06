# Compute Evidence Quality And Manual Review Flags

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Compute Evidence Quality Score and Manual Review Flag for each Video Evidence Report based on video download quality, OCR quality, transcript quality, timeline completeness, audio analysis, hook clarity, and claim uncertainty.

## Acceptance Criteria

- [ ] Each video receives a high, medium, or low Evidence Quality Score.
- [ ] Each Evidence Quality Score includes a short reason.
- [ ] Medium and low confidence reports receive a Manual Review Flag.
- [ ] Unclear first-three-second hooks trigger a Manual Review Flag.
- [ ] OCR failures on visible text trigger a Manual Review Flag.
- [ ] Transcript or language detection failures trigger a Manual Review Flag.
- [ ] The score and flag are stored in structured JSON.

## Blocked By

- `0004-extract-hybrid-timeline-frames.md`
- `0005-add-ocr-evidence-capture.md`
- `0006-add-multilingual-speech-transcription.md`
- `0007-add-baseline-audio-music-trend-analysis.md`
