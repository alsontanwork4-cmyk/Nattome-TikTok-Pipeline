# Delete Skipped Legacy Nested Pipeline Tests

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Delete the skipped `legacy_nested_cli_test` block in `tests/test_batch_analysis_run.py`.

Those skipped tests still describe the retired nested evidence-bundle pipeline, local FFmpeg/OCR/transcription command flags, Cross-Video Markdown output, and CSV Spreadsheet Summary output. Current two-layer Gemini tests should remain as the active regression surface.

## Acceptance Criteria

- [x] The `legacy_nested_cli_test` skip decorator is removed.
- [x] The skipped legacy nested CLI tests are deleted, not re-enabled.
- [x] Current two-layer Gemini tests remain as active coverage for run creation, evidence snapshots, final outputs, Telegram, and cleanup.
- [x] `pytest -q` reports no skipped legacy nested CLI tests.
- [x] No active test still passes removed CLI flags such as `--ffmpeg-bin`, `--ocr-primary-bin`, `--ocr-fallback-bin`, or `--transcription-bin`.

## Blocked By

- `docs/issues/0030-remove-cross-video-markdown-report-output.md`
- `docs/issues/0031-remove-csv-spreadsheet-summary-output.md`
