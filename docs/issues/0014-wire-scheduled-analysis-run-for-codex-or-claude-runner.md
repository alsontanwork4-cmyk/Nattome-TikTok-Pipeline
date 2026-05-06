# Wire Scheduled Analysis Run For Codex Or Claude Runner

Type: HITL

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Define and wire the weekly Scheduled Analysis Run so Codex or Claude Code can execute the same Batch Analysis Run and produce the same Batch Output Set. This slice needs human review because schedule, runner, credentials, and operational expectations affect how the team receives weekly reports.

## Acceptance Criteria

- [ ] The weekly schedule is documented.
- [ ] The automation runner option is documented for Codex and Claude Code.
- [ ] The run uses the same Batch Output Set regardless of runner.
- [ ] Missing Apify, OCR, transcription, FFmpeg, or Telegram setup is reported clearly.
- [ ] The weekly run sends Telegram Delivery only after required batch outputs are produced.
- [ ] Human review confirms schedule, runner, and credential setup.

## Blocked By

- `0013-add-telegram-weekly-evidence-brief-delivery.md`
