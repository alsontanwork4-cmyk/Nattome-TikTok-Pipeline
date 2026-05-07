# Gemini Two-Layer Evidence Pipeline Architecture PRD

## Problem Statement

The current Batch Analysis Run can produce Evidence Bundles, Video Evidence Reports, Cross-Video Pattern Summaries, Structured JSON Output, Spreadsheet Summary Output, Telegram Delivery logs, cleanup logs, and refinement hooks. It works, but the architecture has grown around nested Run Folder paths, raw JSON artifact reads, command-line Tool Stack execution, and boolean-heavy run metadata.

This creates friction for the user in three ways.

First, Run Folders are too deeply nested. A Batch Analysis Run produces folders inside folders inside folders, which makes outputs harder to scan, share, clean up, and automate against.

Second, the Tool Stack is too operationally heavy. Separate FFmpeg, OCR, and transcription command-line paths create setup and maintenance burden. The user wants a simpler, stable, scalable extraction path based on Gemini 2.5 Flash, where Gemini analyzes the raw TikTok video and provides timestamped evidence.

Third, many modules know too much about artifact filenames, JSON shapes, phase ordering, and output status rules. This makes the pipeline harder to change safely. The user wants deeper modules with stronger locality and leverage: a Run Manifest module, an Evidence Bundle Reader/Writer module, a Gemini Tool Stack Adapter, and a pure Shootable Angle generation module.

The architectural goal is to keep Evidence-First Analysis and the existing Nattome domain outputs, while making the implementation easier to navigate, test, scale, and operate.

## Solution

The pipeline will be redesigned around a two-layer Run Folder, Gemini 2.5 Flash evidence extraction, a dedicated Evidence Bundle Reader/Writer, and an incremental Run Manifest.

New Batch Analysis Runs will write only two folder layers:

- the Run Folder itself
- direct child folders such as reports, data, evidence, and logs

No new run should create nested per-video folders. Per-video artifacts will use stable filename prefixes based on rank and candidate ID. For example, a video ranked first will use a prefix like `001_candidate-id` across report, data, and evidence files.

Gemini 2.5 Flash will replace the raw FFmpeg, OCR, and transcription command-line Tool Stack as the primary extraction adapter. Gemini will analyze the source video and produce structured timestamped evidence for visual observations, OCR text, spoken content, audio cues, first-three-second hook evidence, and claim evidence. Gemini will not generate final Shootable Angles. Gemini is the evidence extraction adapter only.

Codex or Claude Code will generate final Shootable Angles from candidate metadata and Gemini evidence. Local logic will own Nattome-specific decisions: avatar, product fit, claim guardrails, brand safety, evidence confidence, ease of production, and Nattome Priority Score.

The Evidence Bundle Reader/Writer will own all file naming, artifact lookup, validation, and missing-artifact states. Downstream modules will consume Evidence Bundle snapshots instead of assembling paths or reading raw JSON files directly.

The Run Manifest will replace the current metadata file. It will be updated incrementally during the run and become the source of truth for configuration, selected candidates, phase records, output paths, evidence indexes, delivery status, cleanup status, and refinement hooks. The human-readable batch index will be generated from the manifest.

The Minimum Eligibility Filter will also be corrected so downloadable video presence is a hard selection rule by default. A debug or preview override remains available when explicitly configured.

## User Stories

1. As a Codex user, I want each Batch Analysis Run to produce a simpler Run Folder, so that I can inspect outputs without opening deeply nested folders.
2. As a Codex user, I want the Run Folder to use at most two folder layers, so that reports, data, evidence, and logs are easy to find.
3. As a Codex user, I want per-video files to share a stable rank and candidate ID prefix, so that related files are easy to identify across output folders.
4. As a Codex user, I want new runs to use the new two-layer layout fully, so that the codebase does not keep writing two competing layouts.
5. As a Codex user, I want historical runs to remain untouched, so that archived outputs do not need migration before this feature can ship.
6. As a Codex user, I want Gemini 2.5 Flash to analyze source TikTok videos, so that the pipeline is simpler and more scalable than separate local extraction tools.
7. As a Codex user, I want Gemini to produce timestamped evidence, so that Video Evidence Reports can still support Evidence-First Analysis.
8. As a Codex user, I want Gemini evidence to include visible text, so that OCR evidence is still available for hook and claim review.
9. As a Codex user, I want Gemini evidence to include spoken content, so that transcript-style evidence is still available for Report Form sections.
10. As a Codex user, I want Gemini evidence to include visual observations, so that the pipeline does not pretend metadata alone explains why a TikTok worked.
11. As a Codex user, I want Gemini evidence to include audio and hook cues, so that Baseline Audio Analysis still has evidence behind it.
12. As a Codex user, I want Gemini evidence to include claim evidence, so that Claim Safety Review can still identify risky health or product claims.
13. As a Codex user, I want Gemini to remain an adapter, so that Nattome domain modules do not become coupled to one vendor's response shape.
14. As a Codex user, I want raw source videos preserved as Evidence Artifacts, so that evidence can be checked later if a report looks wrong.
15. As a Codex user, I want extracted frame images to become optional debug artifacts, so that normal runs stay compact.
16. As a Codex user, I want downloadable video presence enforced by default during candidate selection, so that Batch Analysis Runs are evidence-ready.
17. As a Codex user, I want an explicit override for metadata-only or debug selection previews, so that I can inspect candidate ranking even when video sources are missing.
18. As a Codex user, I want missing video sources to produce a separate exclusion reason, so that upstream scrape quality problems are easy to diagnose.
19. As a maintainer, I want the Evidence Bundle Reader/Writer to own all artifact file names, so that path conventions have strong locality.
20. As a maintainer, I want downstream modules to consume Evidence Bundle snapshots, so that report, quality, claim, and summary code do not manually read artifact files.
21. As a maintainer, I want missing artifacts represented as explicit states, so that downstream modules do not duplicate filesystem checks.
22. As a maintainer, I want a Run Manifest to replace boolean status plumbing, so that phase state is structured and debuggable.
23. As a maintainer, I want the Run Manifest to update incrementally, so that failed or partial runs still explain what happened.
24. As a maintainer, I want phase records to include inputs, outputs, timings, status, and error information, so that retries and diagnostics are easier.
25. As a maintainer, I want the human-readable batch index generated from the Run Manifest, so that output path logic has one source of truth.
26. As a maintainer, I want Shootable Angle generation to be a pure domain module, so that creative rules can be tested without writing files.
27. As a maintainer, I want Gemini to provide evidence but not final Shootable Angles, so that brand and compliance logic stays under local control.
28. As a maintainer, I want each video to produce up to three evidence-backed Shootable Angles, so that strong videos can generate multiple useful ideas without filler.
29. As a maintainer, I want the Nattome Priority Score to keep its six current dimensions and 30-point maximum, so that existing domain language remains stable.
30. As a maintainer, I want Report Form and Cross-Video Pattern Summary rendering to consume structured angle data, so that rendering does not invent creative decisions.
31. As a maintainer, I want the Gemini Tool Stack Adapter to have a narrow interface, so that future adapters can be added without changing report logic.
32. As a maintainer, I want Mixpeek and local Python extraction to remain out of the first implementation, so that the first migration stays focused.
33. As a maintainer, I want tests around the new modules to validate external behavior, so that implementation details can change safely.
34. As a maintainer, I want CLI-scale regression tests to remain, so that the end-to-end Batch Analysis Run still proves core workflow behavior.
35. As a marketing user, I want the final reports to remain evidence-led, so that Nattome does not reuse unsupported claims or fake video observations.
36. As a marketing user, I want the Cross-Video Pattern Summary to stay scannable, so that I can compare hooks, emotional triggers, audio patterns, risky claims, and priority Shootable Angles.
37. As a marketing user, I want Spreadsheet Summary Output to remain available, so that I can review one row per analyzed video.
38. As a marketing user, I want claim guardrails to remain visible in Shootable Angles, so that viral ideas are adapted safely.
39. As an automation runner, I want Scheduled Analysis Runs to produce predictable output paths, so that delivery and cleanup can be automated.
40. As an automation runner, I want Telegram Delivery and cleanup logs listed in the Run Manifest, so that downstream status checks do not need to scan the folder manually.

## Implementation Decisions

- New Batch Analysis Runs will switch fully to the two-layer Run Folder layout.
- The direct child folders under a Run Folder will be organized by output type: reports, data, evidence, and logs.
- New runs will not write the old nested batch output and evidence bundle layout.
- Historical nested runs can remain as archived outputs.
- Per-video files will use a stable prefix made from rank and candidate ID.
- Gemini 2.5 Flash will become the primary Tool Stack Adapter.
- Gemini will analyze raw source video and return structured timestamped evidence.
- Gemini will replace mandatory local frame extraction, OCR command execution, and transcription command execution for normal runs.
- Raw source videos remain durable Evidence Artifacts unless cleanup is explicitly enabled.
- Frame images are optional debug artifacts, not mandatory outputs.
- Mixpeek is not part of the first implementation.
- Local PyAV, PaddleOCR, EasyOCR, faster-whisper, and Whisper adapters are not part of the first implementation.
- The Tool Stack Adapter seam remains explicit so future adapters can be added later.
- Gemini output will be normalized into Nattome evidence concepts before other modules consume it.
- The Evidence Bundle Reader/Writer owns all Run Folder file naming and lookup.
- The Evidence Bundle Reader/Writer exposes one Evidence Bundle snapshot per selected video.
- Evidence Bundle snapshots include source metadata, source video state, Gemini evidence, derived evidence records, claim review, evidence quality, report path, and missing-artifact states.
- Downstream modules consume Evidence Bundle snapshots instead of raw file paths.
- Missing artifacts are represented explicitly by the Reader/Writer.
- The Run Manifest replaces the current metadata file.
- The Run Manifest is updated incrementally during the Batch Analysis Run.
- Phase statuses are structured records, not derived booleans.
- Phase records include phase name, status, inputs, outputs, timing, and error information.
- The Run Manifest is the source of truth for output paths and run status.
- The human-readable batch index is generated from the Run Manifest.
- The Minimum Eligibility Filter enforces downloadable video source presence by default.
- Downloadability at selection time is presence-only.
- Missing downloadable video source is a separate exclusion reason.
- An explicit configuration override can allow metadata-only or debug selection previews.
- Shootable Angle generation becomes a pure domain module.
- Gemini provides evidence only and does not generate final Shootable Angles.
- Codex or Claude Code generates final Shootable Angles from evidence.
- The local Shootable Angle module owns avatar, product fit, claim guardrails, Nattome Priority Score, and final angle shape.
- Each video can produce up to three evidence-backed Shootable Angles.
- Weak filler angles must not be generated just to reach a fixed count.
- Nattome Priority Score keeps the current six dimensions and 30-point maximum.
- The six dimensions remain viral strength, Nattome relevance, evidence confidence, brand safety, ease of production, and product fit.
- Markdown Report Output, Structured JSON Output, Spreadsheet Summary Output, Telegram Delivery, cleanup, and refinement hooks remain required domain capabilities.

## Testing Decisions

- Tests should validate external behavior through module interfaces and generated outputs, not internal helper calls.
- The Minimum Eligibility Filter should have focused tests for downloadable video source enforcement and the explicit override.
- The Gemini Tool Stack Adapter should have tests using fake Gemini responses to prove evidence normalization, failure handling, and missing evidence behavior.
- A small number of integration tests should verify that the adapter can be configured without requiring live Gemini calls in normal test runs.
- The Evidence Bundle Reader/Writer should have focused tests for file naming, prefix generation, snapshot loading, missing-artifact states, and two-layer Run Folder constraints.
- The Run Manifest should have focused tests for incremental phase updates, structured status records, output path registration, failed phase recording, and batch index rendering.
- The Shootable Angle module should have focused tests for one, multiple, and zero evidence-backed angles.
- The Shootable Angle module should have tests proving Gemini evidence is input only and final Nattome rules are local.
- The Nattome Priority Score should have focused tests preserving the six dimensions and 30-point maximum.
- Report Form tests should verify that reports render from structured evidence and angle data.
- Cross-Video Pattern Summary tests should verify that multiple angles per video are compared without creating weak filler.
- CLI-scale tests should remain as regression coverage for full Batch Analysis Run behavior.
- Tests should verify that new runs do not create folders deeper than the Run Folder plus one direct child folder.
- Tests should verify that legacy output writer paths are not used for new runs.
- Tests should verify that missing Gemini credentials or Gemini failures are recorded honestly in the Run Manifest and output evidence states.
- Tests should verify that the pipeline does not fabricate OCR, transcript, hook, visual, audio, or claim evidence when Gemini evidence is missing or incomplete.
- Tests should verify that cleanup preserves durable reports, structured data, spreadsheet output, and manifest state.
- Prior art includes the existing Batch Analysis Run CLI tests, output tests, claim safety tests, evidence quality tests, report tests, Telegram Delivery tests, cleanup tests, and tool adapter tests.

## Out of Scope

- Migrating historical nested Run Folders is out of scope.
- Supporting old and new write layouts at the same time is out of scope.
- Adding Mixpeek as an adapter is out of scope.
- Building a local PyAV, PaddleOCR, EasyOCR, faster-whisper, or Whisper adapter is out of scope.
- Deep Sound Research is out of scope unless it is already represented as a refinement hook.
- Full script generation is out of scope.
- Changing the Report Form section structure is out of scope unless needed to render the same domain content from new evidence.
- Changing the core Nattome Priority Score dimensions is out of scope.
- Removing ease of production from the score is out of scope.
- Changing Telegram Delivery destination behavior is out of scope.
- Changing Scheduled Analysis Run cadence or automation configuration is out of scope.
- Creating a UI is out of scope.
- Uploading outputs to external storage is out of scope.
- Adding corpus-level semantic search across historical runs is out of scope.

## Further Notes

- This PRD supersedes the earlier direction of separate local FFmpeg, OCR, and transcription tooling for the next architecture phase.
- ADR-0001 and ADR-0002 still apply: the pipeline remains batch-first and evidence-first.
- The Gemini adapter must preserve the spirit of Evidence-First Analysis by returning explicit evidence, not unsupported summary claims.
- The two-layer Run Folder constraint is a user requirement and should be treated as a first-class acceptance criterion.
- The architecture should favor deep modules: the interface is the test surface, and file layout, vendor response shape, phase status, and creative scoring rules should each have strong locality.
