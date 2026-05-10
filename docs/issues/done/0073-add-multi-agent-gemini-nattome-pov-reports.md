# Add Two-Agent Gemini Nattome POV Reports

Labels: needs-triage
Type: HITL

## What to build

Add a Phase 2 creative-reporting path after source video snapshotting that uses the official Gemini SDK to produce high-quality, marketer-facing Nattome POV inspiration reports from downloaded TikTok source videos.

The architecture should use two distinct Gemini agents, implemented as sequential Gemini calls with separate role prompts and contracts:

1. **Video Evidence Analyst Agent** watches the source video and extracts timestamped evidence from visuals, spoken audio, visible text, pacing, editing, creator behavior, emotional trigger, hook structure, and claims.
2. **Nattome Creative Strategist Agent** receives the evidence, candidate metadata, and `skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md`, then writes a specific marketer-facing Nattome POV report. Gemini chooses the report format for the specific video.

Python should remain the orchestration and storage layer only. It should not hard-code the creative report format, choose the Nattome angle with deterministic rules, or render marketer-facing sections from a fixed template.

## Product decision

The report quality problem is that rule-driven or template-driven local report generation makes different video reports feel too similar. This slice intentionally moves creative interpretation and final report writing into Gemini role prompts while keeping Python responsible for reliability.

The desired split is:

- Gemini agents decide the analysis, creative framing, report format, and final marketer-facing wording.
- Python downloads videos, uploads files to Gemini, passes brand context, tracks status, saves artifacts, retries failures, and records manifest state.
- Python may validate required machine-level conditions, but it must not replace Gemini's creative judgment with fixed report sections or hard-coded product/angle logic.

## Acceptance criteria

- [ ] The Batch Analysis Run can run a Phase 2 Gemini creative-reporting path after `source_video_snapshots`.
- [ ] The implementation uses the official Gemini SDK package, expected as `google-genai`.
- [ ] The pipeline reads `GEMINI_API_KEY` from environment or `.env`.
- [ ] Missing Gemini credentials are recorded honestly without attempting creative report generation.
- [ ] Each available source video is uploaded or otherwise provided to Gemini using a Gemini-supported video input method.
- [ ] The Video Evidence Analyst Agent has its own prompt, role, input contract, and output contract.
- [ ] The Evidence Analyst output includes timestamped visual observations, spoken content or transcript-style notes, visible text, hook evidence, pacing/editing notes, emotional triggers, creator behavior, and claim evidence when available.
- [ ] The Nattome Creative Strategist Agent has its own prompt, role, input contract, and output contract.
- [ ] The Creative Strategist receives evidence, candidate metadata, and the full Nattome brand POV reference.
- [ ] The Creative Strategist writes the marketer-facing report in a format chosen for that specific video, not a fixed Python-rendered template.
- [ ] The Creative Strategist prompt explicitly asks for a report that is specific, non-generic, useful to a marketer planning a shoot, grounded in evidence, and aligned with Nattome claim safety.
- [ ] The final report must ground recommendations in observable video evidence or explicit Nattome brand guidance.
- [ ] The final report should not invent clinical claims, product outcomes, doctor recommendations, guaranteed relief, cure language, or disease-prevention claims.
- [ ] Python does not contain hard-coded marketer-facing report sections beyond minimal persistence wrappers and status metadata.
- [ ] Python does not make deterministic product/avatar/format decisions that override Gemini's creative report.
- [ ] Python performs only lightweight status validation, such as checking whether a report exists and whether Gemini returned an error.
- [ ] Per-video artifacts use existing stable prefixes, for example `001_<video-id>`.
- [ ] The run writes raw or normalized agent outputs under `data/`.
- [ ] The run writes the final marketer-facing report under `reports/`.
- [ ] The run manifest records each Gemini phase with status, inputs, outputs, model name, and failure details.
- [ ] The pipeline can skip already completed per-video reports on rerun.
- [ ] The pipeline can continue processing other videos when one video fails.
- [ ] Tests use fake Gemini clients and do not require live Gemini credentials or network access.
- [ ] Tests cover completed, missing-credentials, failed-video, and rerun-skip behavior.
- [ ] Documentation explains that Gemini is responsible for creative report format while Python is responsible for orchestration and artifact integrity.

## Suggested output paths

- `data/<prefix>_gemini_evidence.json`
- `data/<prefix>_gemini_creative_response.json`
- `reports/<prefix>_nattome_pov_report.md`

## Suggested manifest phases

- `gemini_video_evidence`
- `gemini_creative_strategy`
- `nattome_pov_reports`

Each phase should support explicit statuses such as `completed`, `partial`, `missing_credentials`, `skipped`, and `failed`.

## Implementation notes

- Prefer sequential per-video processing for the first implementation, with artifact-level idempotency so parallelism can be added later.
- Use one video per Gemini request for best debuggability.
- Default to Gemini's normal video sampling unless a config setting explicitly requests higher FPS for short, fast-cut videos.
- Preserve downloaded source videos as durable evidence artifacts.
- Store enough raw Gemini response detail to debug poor reports without rerunning the whole pipeline.
- Keep prompt files or prompt builders separate by agent role so marketer feedback can tune evidence extraction or creative strategy without touching orchestration code.

## Out of scope

- Building a complex external agent framework.
- Reintroducing FFmpeg, local OCR, or local Whisper as required runtime dependencies.
- Generating reports from fixed Python templates.
- Automatically publishing reports to Telegram, Supabase, or other cloud destinations.
- Full UI changes beyond exposing the generated artifacts if the dashboard already indexes run outputs.

## Blocked by

- Human approval of this architecture and prompt direction.

## Current status

Implemented.

Key implementation points:

- Added `batch_analysis/gemini_reports.py` for the two sequential Gemini agents.
- Added a preferred Nattome POV report outline to the Creative Strategist prompt so Gemini generates reports in the proven creative brief shape without Python rendering section templates.
- Added post-report Telegram delivery from environment-provided `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: a Singapore-time summary message followed by the generated `.md` report document, with delivery recorded separately in the run manifest.
- Wired Phase 2 into `batch_analysis/run.py` immediately after `source_video_snapshots`.
- Added fake-client tests for completed, missing-credentials, failed-video/continue, and rerun-skip behavior.
- Updated README, context, requirements, and the daily workflow contract for `google-genai` and optional `GEMINI_API_KEY`.

Verification:

- `.venv\Scripts\python.exe -m unittest discover -s tests -v`
