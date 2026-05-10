# Nattome TikTok Source Video Pipeline

This context defines the current compact runtime language.

## Active Boundary

The pipeline discovers TikTok candidates, selects the Daily Top Videos, downloads or copies the selected source videos, writes flat snapshot artifacts, and then runs Gemini-powered Nattome POV reporting for available source videos.

Python remains the orchestration and storage layer. Gemini is responsible for video evidence interpretation, creative framing, and final marketer-facing wording using the preferred Nattome POV report outline.

## Terms

**Raw Scrape**:
The ranked Apify TikTok JSON output before eligibility filtering.

**Daily Top Videos Selection**:
The selected handoff containing the eligible top videos for the source-video run.

**Minimum Eligibility Filter**:
The baseline selection filter for views, age, weighted engagement, TikTok link, downloadable video, and exclusion terms.

**Source Video Snapshot Run**:
The batch run that creates one timestamped run folder from a Daily Top Videos Selection.

**Gemini Video Evidence Agent**:
The first Phase 2 Gemini call. It watches one source video and returns timestamped evidence from visuals, spoken audio, visible text, pacing/editing, creator behavior, emotional triggers, hook structure, and claims when available.

**Nattome Creative Strategist Agent**:
The second Phase 2 Gemini call. It receives the evidence, candidate metadata, the full Nattome brand reference, and a preferred report outline, then writes a marketer-facing Nattome POV report.

**Run Folder**:
The timestamped folder under `runs/batch-analysis/` containing raw scrape JSON, Daily Top Videos handoff JSON, selected-batch metadata, per-candidate source metadata, source videos, snapshot JSON, and reports.

**Source Snapshot Index**:
`data/evidence_bundle_index.json`, the flat index linking selected candidates to source-video state and snapshot artifacts.

**Source Video State**:
One of `available`, `missing`, or `failed`. This state is factual and should not be softened.

**Gemini Phase Status**:
One of `completed`, `partial`, `missing_credentials`, `skipped`, or `failed`. Missing credentials must be recorded honestly without attempting report generation.

**Telegram Delivery Phase**:
The post-report delivery phase that sends a Singapore-time summary message and generated Nattome POV `.md` report document to the configured Telegram chat when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are available.

## Active Outputs

- `run_metadata.json`
- `run_manifest.json`
- `data/raw_scrape_all.json`
- `data/daily_selection_top_videos.json`
- `data/selected_batch.json`
- `reports/selected_batch.md`
- `data/evidence_bundle_index.json`
- `data/<rank>_<video-id>_source_metadata.json`
- `data/<rank>_<video-id>_evidence_snapshot.json`
- `data/<rank>_<video-id>_gemini_evidence.json`
- `data/<rank>_<video-id>_gemini_creative_response.json`
- `evidence/<rank>_<video-id>_source_video.<ext>`
- `reports/<rank>_<video-id>_nattome_pov_report.md`

## Rules

- Do not invent analysis results from captions or metadata.
- Do not render marketer-facing Nattome POV reports from fixed Python templates.
- Do not make deterministic Python product, avatar, or creative-angle decisions that override Gemini's creative judgment.
- The Creative Strategist prompt may provide a preferred outline, but Gemini must generate the report content.
- Keep the runtime compact: discovery, selection, source-video snapshotting, Gemini orchestration, manifest.
- Preserve selected candidate rank and source-video state exactly.
- Ground final recommendations in observable video evidence or explicit Nattome brand guidance.
- Do not invent clinical claims, product outcomes, doctor recommendations, guaranteed relief, cure language, or disease-prevention claims.
- Telegram delivery must be recorded separately from report generation. A delivery failure must not delete or invalidate generated report artifacts.
