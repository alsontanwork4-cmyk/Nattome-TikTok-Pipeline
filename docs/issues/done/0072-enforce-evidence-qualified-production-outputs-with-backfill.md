# Enforce Evidence-Qualified Production Outputs With Backfill

Labels: needs-triage
Type: AFK

## What to build

Change the Daily Evidence Run so final marketer-facing production outputs contain only production-qualified candidates: videos with at least one evidence-backed Shootable Angle generated from source-video evidence.

The completed slice should use the Daily Top-3 Selection first, then analyze up to two separate backfill candidates only when needed. It should stop producing metadata-only fallback concepts, fallback Recommended Shoot scripts, or production files when no candidate qualifies.

## Decisions

- The public evidence-analysis CLI has one normal Daily Evidence Run Interface.
- Remove public run modes and public batch-size overrides.
- Remove public one-video debugging mode from current runtime/docs.
- Discovery keeps `--top 30` for raw scrape pool size.
- Discovery removes `--daily-selection-size`.
- Discovery writes structured JSON, not Markdown, for handoffs:
  - `daily_selection_top3.json`
  - `daily_backfill_candidates.json`
- Backfill candidates are a separate candidate set, not part of the canonical Daily Top-3 Selection.
- Analyze Top-3 candidates first.
- Analyze backfill candidates only when a Top-3 candidate does not qualify.
- Backfill cap is two candidates.
- A candidate qualifies for production only when it has at least one generated Shootable Angle.
- Missing download, missing Gemini credentials, Gemini failure, and Gemini output with no evidence-backed Shootable Angle are non-qualifying.
- Missing Gemini credentials is run-level failure: do not attempt backfill and do not create production report/workbook.
- If zero candidates qualify after Top-3 plus backfill, skip final production files entirely.
- If one or two candidates qualify, create final production files with only those candidates.
- Production report sections are renumbered 1..N, while source/original selection rank remains visible in the Source Reference.
- Use neutral final filenames:
  - `production_creative_report_YYYY-MM-DD.md`
  - `production_angle_planning_sheet_YYYY-MM-DD.xlsx`
- Do not write old `top5_*` aliases for new runs.
- Keep dashboard/indexer/report-view fallback support for historical `top5_*` artifacts.
- Structured JSON should distinguish:
  - original Daily Top-3 Selection
  - backfill candidate set
  - analyzed candidates
  - production-qualified candidates
- Cross-Video Pattern Summary used for production should compare only production-qualified videos.
- Telegram sends a failure/status notification when configured and no production files exist, with no production attachments.
- Cloud publication publishes run/audit artifacts even when production outputs are skipped.
- Cleanup applies the same configured retention policy to all analyzed candidates.

## Report-generation skill

Create a repo-local skill at `skills/nattome-production-report-generation/SKILL.md`.

The skill should be a human/agent workflow reference, not a runtime file that Python reads automatically. Python remains responsible for deterministic orchestration, filtering, structured JSON, workbook creation, manifest/cloud/Telegram state, and testable no-output behavior.

The skill should define:

- Production Run Report workflow.
- Manual Single-Video Analysis workflow for a user-provided TikTok link or video.
- Evidence-First Analysis requirement for both workflows.
- A hard rule that metadata-only analysis may produce only candidate previews/manual-review notes, never Shootable Angles or production recommendations.
- Required Claim Safety Review before any Nattome adaptation.
- Exact Markdown headings for the production report.
- The workbook's tabs and fields at a high level.
- Exactly one timed Recommended Shoot per production-qualified video.

## Acceptance criteria

- [x] `scripts/run_batch_analysis.py` no longer exposes public `--mode` or `--batch-size` flags.
- [x] `batch_analysis` no longer depends on public named run modes for normal operation.
- [x] Discovery writes `daily_selection_top3.json` and `daily_backfill_candidates.json`.
- [x] Discovery no longer exposes `--daily-selection-size`.
- [x] Evidence analysis accepts backfill candidates through an explicit CLI argument.
- [x] Top-3 candidates are analyzed before any backfill candidates.
- [x] Backfill candidates are analyzed only when needed to replace non-qualifying Top-3 candidates.
- [x] Final production report/workbook include only candidates with at least one evidence-backed Shootable Angle.
- [x] Final production report/workbook are skipped when zero candidates qualify.
- [x] Missing Gemini credentials creates audit/status artifacts only, not production report/workbook.
- [x] New final production files use neutral `production_*` filenames.
- [x] New runs do not write `top5_*` production files.
- [x] Historical `top5_*` report/workbook artifacts remain discoverable by dashboard/report views.
- [x] Structured JSON records original selection, backfill candidates, analyzed candidates, and production-qualified candidates separately.
- [x] Production-facing Cross-Video Pattern Summary excludes non-qualified candidates.
- [x] Telegram and cloud publication behavior distinguish skipped production outputs from run crashes.
- [x] `skills/nattome-production-report-generation/SKILL.md` exists and defines the report form and manual single-video workflow.
- [x] Tests cover no-output behavior, partial qualification, backfill replacement, missing credentials, neutral filenames, and no metadata-only production concepts.

## Blocked by

- `docs/issues/0071-rename-top-5-operation-to-daily-top-3.md`
