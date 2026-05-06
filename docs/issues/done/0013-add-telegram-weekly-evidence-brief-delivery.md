# Add Telegram Weekly Evidence Brief Delivery

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Send a concise Telegram Delivery message after each completed weekly Batch Analysis Run. The message should include the Weekly Evidence Brief summary, output locations, and top priority Shootable Angles.

## Acceptance Criteria

- [ ] Telegram Delivery reads bot token and chat ID from runtime configuration.
- [ ] Missing Telegram credentials are reported clearly.
- [ ] Telegram Delivery sends a concise summary rather than the full report body.
- [ ] The message includes output locations for markdown, JSON, and spreadsheet outputs.
- [ ] The message includes top priority Shootable Angles.
- [ ] Tests can use a fake sender without sending real Telegram messages.

## Blocked By

- `0011-generate-cross-video-pattern-summary-and-priority-scores.md`
- `0012-generate-structured-json-and-spreadsheet-summary.md`
