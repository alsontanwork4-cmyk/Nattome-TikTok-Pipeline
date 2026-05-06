# Generate Per-Video Evidence Reports

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Generate one Markdown Video Evidence Report per analyzed video using the fixed Report Form. Reports should cite the Evidence Bundle and include evidence sections, virality analysis, Nattome POV, Claim Safety Review, Evidence Quality Score, Manual Review Flag, and Shootable Angles.

## Acceptance Criteria

- [ ] Each analyzed video produces one markdown Video Evidence Report.
- [ ] The report includes Video Reference, Executive Creative Read, First 3 Seconds Hook Audit, Hybrid Timeline, OCR Text Summary, Speech Transcript Summary, Audio/Music Trend Analysis, Virality Breakdown, Nattome POV, Shootable Angles, Claim Safety Review, and Evidence Quality.
- [ ] Each report links back to source TikTok and local evidence artifacts.
- [ ] Each report includes at least one Nattome Shootable Angle.
- [ ] Shootable Angles include hook, avatar, format, product tie-in, script beats, CTA, and claim guardrails.
- [ ] Reports do not claim evidence was inspected when required artifacts are missing.

## Blocked By

- `0004-extract-hybrid-timeline-frames.md`
- `0005-add-ocr-evidence-capture.md`
- `0006-add-multilingual-speech-transcription.md`
- `0007-add-baseline-audio-music-trend-analysis.md`
- `0008-compute-evidence-quality-and-manual-review-flags.md`
- `0009-add-claim-safety-review.md`
