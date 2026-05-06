# Add Multilingual Speech Transcription

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Extract audio from each downloaded TikTok and produce timestamped speech transcript evidence using a multilingual Whisper-style transcription path.

## Acceptance Criteria

- [ ] Audio is extracted from each downloaded video.
- [ ] Timestamped transcript segments are generated for each video.
- [ ] Transcript JSON is stored in each Evidence Bundle.
- [ ] The transcript output includes confidence or uncertainty metadata where available.
- [ ] Code-mixed English-Malay-Chinese speech is handled as a required use case.
- [ ] Missing transcription tooling produces a clear setup error.

## Blocked By

- `0003-download-video-evidence-bundles.md`
