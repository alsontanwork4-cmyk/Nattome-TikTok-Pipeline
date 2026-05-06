# Nattome TikTok OCR Video Evidence Pipeline PRD

## Problem Statement

Nattome needs to understand why TikTok videos in the digestive-health space are engaging, but metadata-only analysis cannot prove what viewers actually saw, heard, read, or reacted to. Captions, views, likes, comments, and shares are useful for discovery, but they do not reveal the first-three-second hook, on-screen subtitles, fast text overlays, speech, audio cues, pacing, claim language, or edit structure.

The marketing team needs a repeatable weekly system that deeply analyzes a selected batch of TikTok videos, finds repeatable creative patterns, protects Nattome from unsafe health claims, and delivers shootable Nattome angles through markdown, structured JSON, spreadsheet summary, and Telegram notification.

## Solution

Build a batch-first, evidence-first TikTok OCR/video analysis pipeline for Nattome.

Each Scheduled Analysis Run will select a Default Batch of 10 TikTok videos using the Minimum Eligibility Filter and Viral Relevance Selection. For each selected TikTok, the system will create an Evidence Bundle containing metadata, downloaded video, Hybrid Timeline frames, OCR timeline, speech transcript, Audio/Music Trend Analysis, and other Evidence Artifacts. It will then generate one Video Evidence Report per video using the fixed Report Form.

Each Batch Analysis Run will also produce a Cross-Video Pattern Summary that identifies repeatable hooks, formats, emotional triggers, audio patterns, risky claims, and priority Nattome Shootable Angles. The batch will produce a Batch Output Set containing Markdown Report Output, Structured JSON Output, and Spreadsheet Summary Output. A Weekly Evidence Brief will be sent through Telegram Delivery after the run completes.

The system should support Multilingual Evidence Capture for English, Malay, Mandarin Chinese, Simplified Chinese, Traditional Chinese, and Manglish or code-mixed English-Malay-Chinese.

## User Stories

1. As a Nattome marketer, I want TikTok videos analyzed from actual video evidence, so that I do not rely on metadata-only guesses.
2. As a Nattome marketer, I want a Default Batch of 10 videos, so that I can find patterns across many videos without reviewing hundreds manually.
3. As a Nattome marketer, I want videos selected by virality, recency, and Nattome relevance, so that the system prioritizes content worth learning from.
4. As a Nattome marketer, I want minimum filters applied before selection, so that tiny, stale, irrelevant, or unsafe videos do not waste analysis time.
5. As a Nattome marketer, I want videos under 10,000 views filtered out by default, so that early noise is not treated as a viral signal.
6. As a Nattome marketer, I want videos older than 30 days filtered out by default, so that weekly reports stay trend-relevant.
7. As a Nattome marketer, I want videos below 3% weighted engagement filtered out by default, so that high-view weak-engagement videos are treated carefully.
8. As a Nattome marketer, I want the system to require a usable TikTok link and downloadable video, so that each report can be audited.
9. As a Nattome marketer, I want one Run Folder per Batch Analysis Run, so that each run is reproducible and easy to archive.
10. As a Nattome marketer, I want each video to have its own Evidence Bundle, so that metadata, video, frames, OCR, transcript, and analysis stay together.
11. As a Nattome marketer, I want each downloaded TikTok video stored as an Evidence Artifact, so that the analysis can be audited later.
12. As a Nattome marketer, I want extracted frames stored as Evidence Artifacts, so that OCR and hook analysis can be traced to visual evidence.
13. As a Nattome marketer, I want optional cleanup of large Evidence Artifacts, so that storage does not grow forever after reports are approved.
14. As a Nattome marketer, I want durable markdown, JSON, and spreadsheet outputs kept after cleanup, so that the business record remains available.
15. As a Nattome marketer, I want a Hybrid Timeline for each video, so that every second is sampled and fast text or scene changes are not missed.
16. As a Nattome marketer, I want extra timeline frames around the first three seconds, so that the hook is analyzed with higher precision.
17. As a Nattome marketer, I want extra timeline frames when on-screen text changes, so that fast subtitle or overlay changes are captured.
18. As a Nattome marketer, I want extra timeline frames when scenes change, so that pacing and edit structure are more accurately represented.
19. As a Nattome marketer, I want OCR on on-screen text, so that creator-added subtitles, text overlays, labels, and visual hooks are captured.
20. As a Nattome marketer, I want timestamped OCR, so that I can see exactly when important text appears.
21. As a Nattome marketer, I want speech transcription, so that spoken hooks, claims, explanations, and CTAs are captured.
22. As a Nattome marketer, I want timestamped speech transcription, so that spoken lines can be mapped to visual moments.
23. As a Nattome marketer, I want Multilingual Evidence Capture, so that Malaysian TikTok videos using English, Malay, Mandarin, Chinese text, and Manglish are analyzed properly.
24. As a Nattome marketer, I want the transcript to handle code-mixed English-Malay-Chinese speech, so that local TikTok language is not lost.
25. As a Nattome marketer, I want OCR to support Simplified and Traditional Chinese, so that Chinese text overlays are captured.
26. As a Nattome marketer, I want OCR to support Malay and English, so that common Malaysian on-screen text is captured.
27. As a Nattome marketer, I want Baseline Audio Analysis on every video, so that sound title, audio format, mood, and hook support are considered.
28. As a Nattome marketer, I want Deep Sound Research only when the sound appears to drive virality, so that sound research effort is focused.
29. As a Nattome marketer, I want the report to say whether Nattome should copy, avoid, or adapt the audio style, so that production choices are clearer.
30. As a Nattome marketer, I want the report to distinguish voiceover, talking head, music-only, and reused sound formats, so that the creative mechanism is clear.
31. As a Nattome marketer, I want a Video Evidence Report for every analyzed video, so that every recommendation has evidence.
32. As a Nattome marketer, I want every Video Evidence Report to follow the same Report Form, so that videos are easy to compare.
33. As a Nattome marketer, I want a Video Reference section, so that I can quickly see link, creator, caption, hashtags, duration, date, and engagement stats.
34. As a Nattome marketer, I want an Executive Creative Read, so that I can quickly decide whether the video should be copied, adapted, or skipped.
35. As a Nattome marketer, I want a First 3 Seconds Hook Audit, so that I can see what stopped the scroll.
36. As a Nattome marketer, I want the Hook Audit to separate visual hook, on-screen text hook, spoken hook, and audio hook, so that I know which layer did the work.
37. As a Nattome marketer, I want a Hybrid Timeline table, so that I can inspect the video second by second.
38. As a Nattome marketer, I want the Hybrid Timeline to include visual/action notes, OCR text, transcript, audio cue, edit note, and creative role, so that each moment is explainable.
39. As a Nattome marketer, I want an OCR Text Summary, so that repeated phrases, subtitle style, and text placement are easy to review.
40. As a Nattome marketer, I want a Speech Transcript Summary, so that claims, CTAs, and important spoken lines are easy to review.
41. As a Nattome marketer, I want Audio/Music Trend Analysis, so that sound contribution is not ignored.
42. As a Nattome marketer, I want a Virality Breakdown, so that hook, pacing, structure, emotional trigger, and why-it-won analysis are clearly stated.
43. As a Nattome marketer, I want the Virality Breakdown to include weaknesses or cautions, so that viral but unsafe patterns are not blindly copied.
44. As a Nattome marketer, I want a Nattome POV section, so that each TikTok pattern is translated into a usable Nattome angle.
45. As a Nattome marketer, I want every Video Evidence Report to include Shootable Angles, so that the team can move from analysis to production direction.
46. As a Nattome marketer, I want each Shootable Angle to include a title, hook, avatar, format, product tie-in, script beats, CTA, and claim guardrails, so that it is ready for creative planning.
47. As a Nattome marketer, I want Shootable Angles instead of full scripts by default, so that the batch report stays focused and scannable.
48. As a Nattome marketer, I want the Cross-Video Pattern Summary to identify which Shootable Angles should become full scripts later, so that scripting work goes to the best candidates.
49. As a Nattome marketer, I want Nattome avatars assigned to Shootable Angles, so that angles target The Sufferer, Maintainer, Pharmacy Browser, Family Caregiver, or Concerned Preventer clearly.
50. As a Nattome marketer, I want product fit stated for DH, DR, or DH-R/recovery, so that creative ideas map to the right product moment.
51. As a Nattome marketer, I want DR tied to faster relief moments, so that reflux, bloating, heartburn, indigestion, and gastric discomfort content is handled consistently.
52. As a Nattome marketer, I want DH tied to daily digestive maintenance, so that routine and prevention-style content has a clear product role.
53. As a Nattome marketer, I want DH-R/recovery tied to deeper repair contexts, so that recovery angles are not confused with immediate relief.
54. As a Nattome marketer, I want Claim Safety Review on every report, so that viral health claims are not reused unsafely.
55. As a Nattome marketer, I want cure claims flagged, so that Nattome does not promise cures.
56. As a Nattome marketer, I want guaranteed outcomes flagged, so that Nattome does not overpromise.
57. As a Nattome marketer, I want one-night fix claims flagged, so that Nattome avoids exaggerated relief language.
58. As a Nattome marketer, I want cancer prevention claims flagged, so that Nattome avoids prohibited or unsafe health messaging.
59. As a Nattome marketer, I want zero-side-effect claims flagged, so that Nattome avoids unsupported safety guarantees.
60. As a Nattome marketer, I want detox and cleanse claims flagged, so that Nattome stays away from pseudoscience.
61. As a Nattome marketer, I want unverified doctor-recommended claims flagged, so that authority claims are not invented.
62. As a Nattome marketer, I want unsupported clinical percentages flagged, so that clinical language stays substantiated.
63. As a Nattome marketer, I want aggressive competitor claims flagged, so that Nattome does not attack competitors without approval.
64. As a Nattome marketer, I want unsafe TikTok claims reframed into Nattome-safe language, so that viral ideas can still become usable angles.
65. As a Nattome marketer, I want Evidence Quality Score on every Video Evidence Report, so that I know whether to trust the analysis.
66. As a Nattome marketer, I want Evidence Quality Score to be high, medium, or low with a reason, so that uncertainty is visible.
67. As a Nattome marketer, I want Manual Review Flag when evidence quality is medium or low, so that risky reports get human inspection.
68. As a Nattome marketer, I want Manual Review Flag when the first three seconds are unclear, so that hook analysis is not guessed.
69. As a Nattome marketer, I want Manual Review Flag when OCR fails on visible text, so that missing text is not treated as absent text.
70. As a Nattome marketer, I want Manual Review Flag when transcript language detection fails, so that multilingual uncertainty is not hidden.
71. As a Nattome marketer, I want Manual Review Flag when medical claims are detected, so that claim safety gets human attention.
72. As a Nattome marketer, I want Manual Review Flag when the Nattome angle depends on an unverified claim, so that risky recommendations are not used blindly.
73. As a Nattome marketer, I want a Cross-Video Pattern Summary, so that I can see patterns across the batch instead of reading disconnected reports.
74. As a Nattome marketer, I want the Cross-Video Pattern Summary to compare hooks, formats, emotional triggers, audio patterns, risky claims, and Nattome opportunities, so that weekly learning compounds.
75. As a Nattome marketer, I want Nattome Priority Score, so that priority is not based on views alone.
76. As a Nattome marketer, I want Nattome Priority Score to include viral strength, Nattome relevance, evidence confidence, brand safety, ease of production, and product fit, so that shoot priority is balanced.
77. As a Nattome marketer, I want Nattome Priority Score out of 30 points, so that different angles can be compared quickly.
78. As a Nattome marketer, I want the batch summary to identify the top priority Shootable Angles, so that the team knows what to shoot first.
79. As a Nattome marketer, I want Markdown Report Output, so that detailed reports are readable by humans.
80. As a Nattome marketer, I want Structured JSON Output, so that evidence, scoring, and recommendations can be reused by automation later.
81. As a Nattome marketer, I want Spreadsheet Summary Output, so that the team can scan one row per video.
82. As a Nattome marketer, I want the spreadsheet to include link, topic, hook type, format, emotional trigger, avatar, product fit, priority score, evidence quality, and recommended angle, so that batch comparison is fast.
83. As a Nattome marketer, I want a Weekly Evidence Brief, so that the team receives a recurring summary without manually running the system.
84. As a Nattome marketer, I want Telegram Delivery after each weekly run, so that the team gets the results where they already communicate.
85. As a Nattome marketer, I want Telegram Delivery to include the weekly summary, output locations, and top priority Shootable Angles, so that the message is actionable.
86. As a Nattome operator, I want missing credentials or tool setup reported clearly, so that failed automations do not fabricate analysis.
87. As a Nattome operator, I want the Scheduled Analysis Run to support Codex or Claude Code as the runner, so that the automation can run in the available agent environment.
88. As a Nattome operator, I want the output format to stay the same regardless of runner, so that switching runners does not break downstream usage.
89. As a Nattome operator, I want Telegram bot token and chat ID configuration handled as runtime credentials, so that secrets are not embedded in reports.
90. As a Nattome operator, I want the pipeline built in phases, so that downloading, evidence extraction, reporting, and refinements can be validated progressively.
91. As a Nattome operator, I want Phase 1 to create Run Folders, select videos, download videos, store metadata, and output a batch index, so that the foundation works before OCR is added.
92. As a Nattome operator, I want Phase 2 to extract frames, OCR, transcribe, and capture audio analysis, so that evidence can be inspected before report generation.
93. As a Nattome operator, I want Phase 3 to generate reports, JSON, spreadsheet, quality scores, manual flags, and claim reviews, so that the feature becomes useful to the marketing team.
94. As a Nattome operator, I want Phase 4 to add Deep Sound Research, multilingual improvements, cleanup, and full-script generation for selected winners, so that the system can mature after the core workflow works.
95. As a Nattome operator, I want PaddleOCR as the primary OCR engine, so that Chinese and mixed text overlays are handled better than with a basic OCR fallback.
96. As a Nattome operator, I want Tesseract as a fallback OCR engine, so that the system has a simpler backup path when primary OCR is unavailable.
97. As a Nattome operator, I want FFmpeg used for video, audio, and frame extraction, so that media processing is stable and replaceable.
98. As a Nattome operator, I want Whisper-style multilingual transcription, so that speech evidence works across Malaysian content.
99. As a Nattome operator, I want Apify used for TikTok discovery and download, so that the current scraping approach can evolve into the evidence pipeline.
100. As a Nattome decision-maker, I want the system to separate what made a TikTok viral from what Nattome can safely reuse, so that growth does not damage brand trust.

## Implementation Decisions

- The system will follow the existing domain glossary and ADRs for batch-first, evidence-first TikTok analysis.
- The system will build a Batch Analysis Run as the default workflow, with one-video mode only for debugging or manually pasted URLs.
- The default batch size will be 10 videos. Quick mode may analyze 5 videos, debug mode may analyze 1 video, and deep weekly research may analyze 20 videos.
- Video selection will use Minimum Eligibility Filter first, then Viral Relevance Selection.
- Minimum Filter Thresholds will default to at least 10,000 views, no older than 30 days, at least 3% weighted engagement rate, a usable TikTok link, a downloadable video, and relevance to Nattome.
- The selection model will not force fixed category quotas. It will rank by virality, recency, and Nattome relevance.
- Each Batch Analysis Run will create one Run Folder.
- Each selected video will have one per-video folder containing its Evidence Bundle, Evidence Artifacts, and Video Evidence Report.
- Downloaded videos, frames, subtitles, OCR outputs, transcripts, and audio outputs are Evidence Artifacts, not marketing assets.
- Evidence Artifacts may be cleaned up after report approval, but markdown reports, Structured JSON Output, and Spreadsheet Summary Output are durable records.
- The Evidence Bundle module should be a deep module with a stable interface for reading and writing all evidence for one video.
- The Run Folder module should be a deep module that owns run naming, batch-level output placement, and per-video folder organization.
- The Discovery and Selection module should encapsulate Apify candidate ingestion, Minimum Eligibility Filter, Viral Relevance Selection, and batch size modes.
- The Video Download module should encapsulate video download, source link preservation, retry behavior, and download failure reporting.
- The Hybrid Timeline module should encapsulate frame extraction every second, extra hook frames, text-change frames, scene-change frames, and timeline metadata.
- The OCR module should use PaddleOCR as the primary OCR engine and Tesseract as fallback.
- The OCR module should support English, Malay, Mandarin Chinese, Simplified Chinese, Traditional Chinese, and Manglish/code-mixed evidence where OCR can reasonably capture the text.
- The Transcription module should use Whisper-style multilingual transcription and preserve timestamped speech segments.
- The Audio/Music Trend Analysis module should produce Baseline Audio Analysis for every video and Deep Sound Research only when the sound appears to be a viral mechanism.
- The Evidence Quality module should compute high, medium, or low Evidence Quality Score with a short reason.
- The Manual Review module should produce Manual Review Flag when evidence quality is medium or low, the first three seconds are unclear, OCR fails on visible text, transcript language detection fails, medical claims are detected, or the Nattome angle depends on an unverified claim.
- The Claim Safety module should identify cure claims, guaranteed outcomes, one-night fixes, cancer prevention claims, zero-side-effect claims, detox or cleanse claims, unverified doctor-recommended claims, unsupported clinical percentages, and aggressive competitor claims.
- The Claim Safety module should provide Nattome-safe reuse guidance: reuse, soften, avoid, or reframe.
- The Report Generator module should produce one Video Evidence Report per video using the fixed Report Form.
- The Report Generator module should produce one Cross-Video Pattern Summary per Batch Analysis Run.
- The Structured JSON Output module should preserve batch metadata, selection decisions, Evidence Bundle indexes, Hybrid Timeline, OCR, transcript, audio analysis, virality analysis, claim safety review, quality score, manual review flag, Shootable Angles, and Nattome Priority Score.
- The Spreadsheet Summary Output module should produce a scannable batch-level spreadsheet with one row per analyzed video and selected columns for marketing comparison.
- The Shootable Angle module should generate hooks, avatars, formats, product tie-ins, script beats, CTAs, and claim guardrails, but not full final scripts by default.
- The Nattome Priority Score module should score viral strength, Nattome relevance, evidence confidence, brand safety, ease of production, and product fit, for a total score out of 30.
- The Telegram Delivery module should send a weekly summary message containing the Weekly Evidence Brief, output locations, and top priority Shootable Angles.
- Telegram Delivery should require runtime configuration for bot token and chat ID.
- The Scheduled Analysis Run should be runner-agnostic and support Codex or Claude Code as the automation runner.
- Missing credentials, missing Apify access, failed downloads, missing FFmpeg, missing OCR tooling, missing transcription tooling, or missing Telegram setup should be reported clearly instead of fabricating results.
- The pipeline will be implemented in four phases: Download + Run Folder, Evidence Extraction, Report Generation, and Refinement.
- Phase 1 will include candidate selection, run folder creation, video download, metadata storage, and basic batch index output.
- Phase 2 will include Hybrid Timeline extraction, OCR, transcription, Baseline Audio Analysis, and evidence JSON storage.
- Phase 3 will include Video Evidence Reports, Cross-Video Pattern Summary, Spreadsheet Summary Output, Structured JSON Output, Evidence Quality Scores, Manual Review Flags, Claim Safety Reviews, and Telegram Delivery.
- Phase 4 will include Deep Sound Research, multilingual quality improvements, Evidence Artifact cleanup, and full-script generation for selected Shootable Angles.
- Full scripts, shot lists, voiceovers, captions, and final production scripts are deferred until selected winners are chosen from the Cross-Video Pattern Summary.

## Testing Decisions

- Tests should focus on external behavior and output contracts, not internal implementation details.
- The Discovery and Selection module should be tested with fixed candidate fixtures to prove Minimum Eligibility Filter and Viral Relevance Selection choose expected videos.
- Selection tests should cover minimum views, maximum age, weighted engagement, missing link, failed download eligibility, Nattome relevance, and unsafe content exclusion.
- Run Folder tests should verify that a Batch Analysis Run produces the expected batch-level outputs and per-video folders.
- Evidence Bundle tests should verify that metadata, video references, OCR, transcript, audio analysis, and timeline evidence are written and read consistently.
- Hybrid Timeline tests should verify one-second baseline sampling and extra samples for hook moments, text changes, and scene changes using small controlled media fixtures.
- OCR module tests should use image fixtures containing English, Malay, Simplified Chinese, Traditional Chinese, and mixed-language text where feasible.
- OCR tests should assert extracted text presence and confidence handling rather than exact OCR perfection for every character.
- Transcription tests should use short audio fixtures and verify timestamped segment structure, language metadata, and confidence handling.
- Audio/Music Trend Analysis tests should verify Baseline Audio Analysis is always present and Deep Sound Research is only required when sound is marked as a likely viral driver.
- Evidence Quality Score tests should cover high, medium, and low confidence scenarios.
- Manual Review Flag tests should cover medium quality, low quality, unclear hook, failed OCR, failed language detection, medical claims, and unverified claim dependency.
- Claim Safety Review tests should cover cure claims, guaranteed outcomes, one-night fix claims, cancer prevention claims, zero-side-effect claims, detox claims, unverified doctor claims, unsupported clinical percentages, and competitor attacks.
- Report Generator tests should verify the fixed Report Form sections are present for every Video Evidence Report.
- Cross-Video Pattern Summary tests should verify patterns are aggregated across multiple Video Evidence Reports.
- Nattome Priority Score tests should verify the six dimensions and 30-point total.
- Shootable Angle tests should verify output includes angle title, hook, avatar, format, product tie-in, script beats, CTA, and claim guardrails.
- Spreadsheet Summary Output tests should verify one row per analyzed video and required columns for link, topic, hook type, format, emotional trigger, avatar, product fit, priority score, evidence quality, and recommended angle.
- Structured JSON Output tests should verify the JSON schema is stable enough for later automation and contains evidence, scoring, and recommendations.
- Telegram Delivery tests should use a fake sender and verify message content without sending real Telegram messages.
- Scheduled Analysis Run tests should verify missing credentials and missing tools are reported clearly.
- End-to-end smoke tests should run a tiny one-video or fixture-based Batch Analysis Run and verify markdown, JSON, and spreadsheet outputs are produced.
- Prior art for testing includes the existing Apify scraping workflow and markdown daily brief output; these should guide fixture shape and report expectations.

## Out of Scope

- Full production scripts for every Shootable Angle are out of scope for the default batch report.
- Final shot lists, voiceover scripts, captions, and production-ready creative assets are out of scope until top Shootable Angles are selected.
- Manual human watching of every video is out of scope as the default workflow, though Manual Review Flags may require human inspection.
- Replacing Apify with another TikTok provider is out of scope for the initial implementation.
- A dashboard UI is out of scope.
- Notion, Google Sheets, or CRM publishing is out of scope unless added later.
- Legal approval of final medical claims is out of scope; the system can flag and reframe claims, but cannot replace regulatory or legal review.
- Storing downloaded TikTok videos as marketing assets is out of scope.
- Guaranteeing perfect OCR or transcription across all TikTok styles is out of scope.
- Deep Sound Research for every video is out of scope; it is only required when sound appears to be part of the viral mechanism.

## Further Notes

- The PRD follows the agreed domain language in the Nattome TikTok Video Analysis context.
- The PRD respects the ADR decision to use batch evidence reports rather than metadata-only reporting or one-off OCR.
- The PRD respects the ADR decision to use an evidence-first tool stack with Apify, FFmpeg, PaddleOCR, Tesseract fallback, Whisper-style multilingual transcription, markdown, JSON, and XLSX outputs.
- The system should never claim it watched or inspected video evidence unless the Evidence Bundle was actually downloaded, extracted, OCRed, and transcribed.
- The weekly automation should report missing setup honestly rather than fabricate trend analysis.
- Telegram Delivery should send a concise message, not the entire report body, with links or output locations plus top priority Shootable Angles.
- The implementation should remain runner-agnostic so Codex or Claude Code can execute the same workflow.
