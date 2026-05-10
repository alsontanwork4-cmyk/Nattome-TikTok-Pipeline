# Marketer Scrape Quality Dashboard PRD

## Problem Statement

Nattome's TikTok Content Discovery Pipeline already produces useful artifacts: raw Apify scrapes, Daily Discovery handoffs, Batch Analysis Runs, Video Evidence Reports, Top 5 Creative Production Reports, Excel planning workbooks, structured JSON, run manifests, logs, PRDs, ADRs, and domain documentation. Those artifacts are valuable, but a Nattome marketer still has to navigate folders and files to answer basic operating questions:

- Did the latest scrape return good Nattome-relevant TikToks?
- Which keywords, hashtags, or competitor profiles helped or hurt scrape quality?
- Did the pipeline process the selected videos cleanly?
- What changed in the scrape configuration before a quality improvement or drop?
- Which raw scraped videos look promising, irrelevant, or noisy?
- Which TikTok patterns are emerging across runs?
- Which Nattome POVs are approved and reusable?
- How does the pipeline work, and where are the supporting architecture and tool decisions?

The current file-based workflow is especially hard for a new marketer because raw scraped videos, selected candidates, run health, final reports, and architecture documentation are spread across different folders. The marketer needs a single browsable control room that explains scrape quality, exposes pipeline health, allows safe direct editing of scrape settings, and preserves the current evidence-first artifacts as the audit source of truth.

## Solution

Build a local web dashboard for Nattome marketers that sits on top of the existing TikTok Content Discovery Pipeline.

The dashboard will not replace the existing Markdown, JSON, Excel, run folders, skills, or documentation. Instead, it will read and index those artifacts into a dashboard-owned SQLite cache so marketers can browse, search, and monitor the pipeline from one place.

The first screen will be a Latest Run Overview focused on marketer operations. It will show a top-level Scrape Quality Score, a visually separate Pipeline Health summary, the latest run timestamp, the next scheduled run, the current production config version, the top scraped videos, the top quality drivers, and clear actions for running the pipeline or editing settings.

The Scrape Quality Score will measure scrape quality only. It will not include claim safety, manual review burden, or evidence extraction success. Those belong in the separate Pipeline Health area. A scrape below 60 should be visible as needing attention, but it should not automatically change future runs.

Marketers will be allowed to directly edit production scrape settings through validated forms. Changes affect the next scheduled run automatically and are recorded in a versioned config history with rollback support. Marketers can also trigger immediate manual runs:

- Run scrape now: fast scrape/discovery feedback.
- Run full pipeline: slower end-to-end scrape, selection, evidence analysis, reports, Excel workbook, and delivery.

The dashboard's primary content object will be the raw scraped video, not only selected or analyzed videos. Each raw video will show metadata, source input, engagement, relevance, status, and outbound TikTok link. The dashboard will not embed or locally play downloaded TikTok videos in MVP.

The dashboard does not include in-app raw-video review forms. Recommendations remain advisory and link back to supporting videos, sources, and runs.

The dashboard will include editable Approved Pattern Library and Nattome POV Library sections. Candidate Patterns can be auto-generated from batch/run analysis, then marketers can approve and edit them into canonical patterns. The Pattern Library captures external TikTok mechanics. The Nattome POV Library captures Nattome's owned brand-safe interpretation, marketing territory, product/campaign/market targeting, and adaptation rules.

The dashboard will also expose full architecture and tool-decision material in a browsable Pipeline Architecture section. Architecture docs, PRDs, ADRs, and raw pipeline outputs remain read-only.

The MVP is single-user and local, but all mutable dashboard-owned records should include `created_by`, `updated_by`, timestamps, and versioning fields so the model can migrate to multi-user or hosted use later.

## User Stories

1. As a Nattome marketer, I want to open one dashboard, so that I can monitor the TikTok Content Discovery Pipeline without browsing repo folders manually.
2. As a Nattome marketer, I want the first screen to show the Latest Run Overview, so that I immediately know whether the latest scrape was useful.
3. As a Nattome marketer, I want a top-level Scrape Quality Score, so that I can quickly judge whether the latest scrape needs attention.
4. As a Nattome marketer, I want the Scrape Quality Score to focus only on scrape quality, so that downstream evidence or report failures do not confuse the sourcing signal.
5. As a Nattome marketer, I want Scrape Quality and Pipeline Health to be visually separate, so that I can tell whether sourcing failed or processing failed.
6. As a Nattome marketer, I want scrape quality to show strong, usable, and needs-attention bands, so that I can prioritize action quickly.
7. As a Nattome marketer, I want a scrape below 60 to be flagged, so that I know when settings may need review.
8. As a Nattome marketer, I do not want a low scrape score to auto-change future runs, so that pipeline behavior remains predictable.
9. As a Nattome marketer, I want to see raw candidate count, eligible count, selected count, average relevance, freshness, engagement, and duplicate/noise drivers, so that the score is explainable.
10. As a Nattome marketer, I want to see top quality drivers, so that I know whether a scrape was weak because of source inputs, stale videos, low relevance, low volume, or noise.
11. As a Nattome marketer, I want Pipeline Health visible on the same dashboard, so that I know whether the system processed the scrape into usable outputs.
12. As a Nattome marketer, I want Pipeline Health to show Apify scrape status, raw candidate file status, selected batch status, source video download availability, Gemini evidence status, report generation, Excel generation, Telegram delivery, and phase errors, so that I can detect operational problems.
13. As a Nattome marketer, I want errors summarized in plain language first, so that I understand the business impact without reading logs.
14. As a maintainer, I want technical error details expandable, so that phase status, log paths, exception text, raw JSON, and timestamps are still available for debugging.
15. As a Nattome marketer, I want error severity levels, so that I can distinguish info, warnings, errors, and blocked runs.
16. As a Nattome marketer, I want every raw scraped video to be browsable, so that I can inspect overall scrape quality instead of only seeing selected winners.
17. As a Nattome marketer, I want each raw video to show author, caption, hashtags, source input, views, likes, comments, shares, created date, relevance, engagement, and status, so that I can evaluate usefulness quickly.
18. As a Nattome marketer, I want raw videos to show selection status, so that I can tell whether a video is raw only, eligible, selected, or analyzed.
19. As a Nattome marketer, I want raw videos to show whether a downloadable video was available, so that I can understand selection and pipeline readiness.
20. As a Nattome marketer, I want outbound TikTok links, so that I can inspect the original video when needed.
21. As a Nattome marketer, I do not want local video playback in MVP, so that the dashboard stays lighter and avoids media handling complexity.
22. As a Nattome marketer, I want raw videos to remain read-only in the dashboard, so that the app stays focused on monitoring and settings.
23. As a Nattome marketer, I want recommendations to come from scrape quality drivers, so that they are grounded in pipeline data.
24. As a Nattome marketer, I want repeated videos to be recognizable by TikTok video ID, so that repeated source quality can still be inspected.
25. As a Nattome marketer, I do not want in-app video labels or notes, so that the dashboard stays uncluttered.
26. As a Nattome marketer, I want recommendations to show supporting evidence, so that I can judge whether the suggestion is credible.
27. As a Nattome marketer, I want recommendations to remain passive, so that settings only change when I explicitly edit them.
28. As a Nattome marketer, I want to mark recommendations as accepted, ignored, or needs more data, so that the dashboard can track recommendation usefulness.
29. As a Nattome marketer, I want recommendations to link to supporting videos, sources, and runs, so that I can audit the reasoning.
30. As a Nattome marketer, I want recommendations to resolve when the underlying configuration changes, so that stale recommendations do not clutter the dashboard.
31. As a Nattome marketer, I want to directly edit scrape settings, so that I can improve scrape quality without asking a developer for every keyword or threshold change.
32. As a Nattome marketer, I want settings edited through validated forms, so that I do not break the config with invalid JSON.
33. As a Nattome marketer, I want to edit hashtags through a chip input that strips `#`, so that the input matches scraper expectations.
34. As a Nattome marketer, I want to edit keywords through a chip or multiline input, so that search terms are easy to manage.
35. As a Nattome marketer, I want to edit competitor profiles through a chip input that strips `@`, so that profile source inputs are easy to manage.
36. As a Nattome marketer, I want to edit scrape scope, so that I can run all sources or only hashtags, keywords, or profiles.
37. As a Nattome marketer, I want to edit results per input, top N, and daily selection size, so that scrape size and handoff size are adjustable.
38. As a Nattome marketer, I want to edit minimum views, maximum age days, minimum weighted engagement rate, and downloadable-video requirement, so that the Minimum Eligibility Filter can be tuned.
39. As a Nattome marketer, I want to edit exclusion terms, so that known low-quality topics or phrases can be avoided.
40. As a Nattome marketer, I want a required reason when saving production setting changes, so that config history is understandable later.
41. As a Nattome marketer, I want setting changes to affect the next scheduled run automatically, so that I do not need a separate publish step.
42. As a Nattome marketer, I want every setting change versioned, so that I can see what changed before a quality improvement or drop.
43. As a Nattome marketer, I want to see the config version that the next scheduled run will use, so that production behavior is clear.
44. As a Nattome marketer, I want one-click rollback to a previous config version, so that I can recover from bad settings.
45. As a maintainer, I want API keys, actor ID, Gemini model, output paths, cleanup deletion settings, Telegram credentials, report schema, and scoring internals read-only in MVP, so that marketer-facing editing does not break pipeline internals.
46. As a Nattome marketer, I want to run a scrape immediately after changing settings, so that I can get fast feedback.
47. As a Nattome marketer, I want manual scrape runs to be labeled separately from scheduled runs, so that run history stays interpretable.
48. As a Nattome marketer, I want manual runs to never overwrite scheduled deliverables, so that experiments do not destroy audit records.
49. As a Nattome marketer, I want a Run scrape now action, so that I can test source quality quickly.
50. As a Nattome marketer, I want a Run full pipeline action, so that I can produce evidence, reports, and Excel outputs when needed.
51. As a Nattome marketer, I want run actions to show estimated runtime and expected outputs, so that I know whether I am launching a quick scrape or a slower evidence run.
52. As a Nattome marketer, I want run progress and status visible, so that I know whether a manual run is still working or failed.
53. As a Nattome marketer, I want completed manual runs indexed automatically, so that results appear in the dashboard without extra work.
54. As a Nattome marketer, I want scheduled behavior to distinguish daily scrape/discovery and weekly full pipeline runs, so that I understand which schedule produces which output.
55. As a Nattome marketer, I want Run History optimized for trends, so that I can see whether scrape quality improves after settings changes.
56. As a Nattome marketer, I want Run History to show run timestamp, run type, config version, scrape score, candidate counts, relevance, engagement, freshness, duplicate/noise score, pipeline status, top issue, and output links, so that each run is scannable.
57. As a Nattome marketer, I want trend charts for score, volume, eligibility yield, relevance, engagement, and config version overlays, so that I can connect quality changes to config changes.
58. As a Nattome marketer, I want to drill into a run, so that I can see raw videos, selected videos, quality drivers, pipeline phases, logs, and linked outputs.
59. As a Nattome marketer, I want direct links to existing Markdown reports and Excel workbooks, so that current deliverables remain useful.
60. As a Nattome marketer, I want the dashboard to sit on top of existing deliverables, so that current Markdown, JSON, Excel, and run-folder audit records are preserved.
61. As a Nattome marketer, I want a Pattern Library, so that reusable TikTok mechanics are easy to find.
62. As a Nattome marketer, I want Candidate Patterns auto-generated from runs, so that emerging patterns are surfaced without manual work.
63. As a Nattome marketer, I want to approve and edit Candidate Patterns into Approved Patterns, so that the canonical Pattern Library stays clean.
64. As a Nattome marketer, I want Approved Patterns to include pattern name, hook type, format type, emotional trigger, source videos, why it works, Nattome adaptation, shoot difficulty, freshness, performance evidence, approval metadata, related POVs, and avoid notes, so that each entry is reusable.
65. As a Nattome marketer, I want patterns to represent external TikTok mechanics, so that source virality is separated from Nattome's interpretation.
66. As a Nattome marketer, I want a Nattome POV Library, so that approved brand-safe angles and messaging territories are easy to browse.
67. As a Nattome marketer, I want Nattome POV entries to represent Nattome's owned interpretation and adaptation rules, so that the team does not copy unsafe viral claims directly.
68. As a Nattome marketer, I want to edit Approved Pattern Library entries inside the dashboard, so that marketing knowledge can evolve without code changes.
69. As a Nattome marketer, I want to edit Nattome POV Library entries inside the dashboard, so that brand POVs remain current.
70. As a Nattome marketer, I want Pattern and POV entries to support product, campaign, market, language, audience/avatar, symptom/occasion, channel, status, and source links, so that the library can support future campaigns.
71. As a Nattome marketer, I want default library targeting values for Nattome, Malaysia, and mixed or English language, so that new entries start from sensible defaults.
72. As a Nattome marketer, I want Pattern and POV version history, so that changes to marketing memory are traceable.
73. As a Nattome marketer, I want architecture and tool decisions visible, so that I can understand how the pipeline works.
74. As a Nattome marketer, I want the Pipeline Architecture section to include the full architecture, tool stack, PRDs, ADRs, phase/status map, file/output map, and data lineage, so that a new person can learn the system.
75. As a maintainer, I want architecture docs read-only in the dashboard, so that canonical engineering documentation remains controlled.
76. As a Nattome marketer, I want global search, so that I can find videos, runs, patterns, POVs, notes, reports, and docs from one place.
77. As a Nattome marketer, I want faceted filtering, so that I can browse by run date, run type, config version, source input, video status, score band, relevance, engagement, freshness, author, hashtag, topic, pattern, POV, market, campaign, product, and pipeline phase.
78. As a Nattome marketer, I want to export filtered raw videos to CSV, so that I can share or analyze a filtered set externally.
79. As a Nattome marketer, I want to export run summaries to CSV, so that I can review scrape trends outside the dashboard.
80. As a Nattome marketer, I want to export approved patterns and Nattome POVs to Markdown, so that the marketing library can be shared in document form.
81. As a Nattome marketer, I do not want a custom deck or report builder in MVP, so that the first version stays focused on monitoring.
82. As a maintainer, I want a dashboard-owned SQLite index/cache, so that filtering, search, config history, quality scores, recommendations, patterns, POVs, and docs index are fast and durable.
83. As a maintainer, I want existing pipeline artifacts to remain the source of truth, so that the dashboard does not replace run folders or evidence outputs.
84. As a maintainer, I want the SQLite index to be rebuildable from artifacts plus dashboard-owned state, so that corrupted or stale indexes can be repaired.
85. As a maintainer, I want approved patterns, POV edits, and config history to be durable dashboard-owned state, so that user work is not lost during reindexing.
86. As a maintainer, I want the MVP to be local and single-user, so that implementation stays practical for the current workflow.
87. As a maintainer, I want mutable records to include `created_by`, `updated_by`, `created_at`, and `updated_at`, so that future multi-user migration is not blocked.
88. As a maintainer, I want manual runs to record `triggered_by`, so that run provenance is preserved.
89. As a maintainer, I want config versions to record old value, new value, reason, timestamp, and user, so that scrape quality changes can be audited.
90. As a maintainer, I want deep modules for artifact indexing, quality scoring, settings validation, config versioning, run orchestration, recommendations, and library curation, so that the dashboard remains testable.

## Implementation Decisions

- The dashboard will be a local web app.
- The MVP is single-user/local.
- The domain model should be multi-user-ready through attribution and timestamps.
- The dashboard will sit on top of existing pipeline artifacts instead of replacing them.
- Existing raw scrapes, Batch Analysis Runs, final reports, Excel workbooks, structured JSON, logs, skills, PRDs, ADRs, and domain docs remain source artifacts.
- The dashboard will create and maintain a SQLite index/cache.
- SQLite stores normalized query records plus dashboard-owned mutable state.
- The SQLite index should be rebuildable from repo artifacts plus durable dashboard-owned state.
- The first screen will be Latest Run Overview.
- Latest Run Overview will show Scrape Quality Score, Pipeline Health, latest run, next scheduled run, config version, top scraped videos, quality drivers, and primary actions.
- Scrape Quality Score is a scrape-only score.
- Scrape Quality Score excludes claim/brand-safety risk, manual review burden, and evidence extraction success.
- Claim safety, manual review, extraction, reports, Excel generation, and delivery belong to Pipeline Health.
- Scrape Quality Score will use a 100-point model.
- Scrape Quality Score dimensions are candidate volume, eligibility yield, Nattome relevance, freshness, engagement strength, and duplicate/noise control.
- Recommended Scrape Quality Score weighting is 25 candidate volume, 20 eligibility yield, 20 Nattome relevance, 15 freshness, 15 engagement strength, and 5 duplicate/noise control.
- Score bands are 80-100 strong scrape, 60-79 usable scrape, and below 60 needs attention.
- A score below 60 creates a visible dashboard warning and recommendations only.
- A score below 60 does not automatically change future scheduled runs.
- Pipeline Health will be visually separate from Scrape Quality.
- Pipeline Health shows phase status and plain-language impact summaries.
- Technical errors are expandable below impact summaries.
- Pipeline Health severity levels are info, warning, error, and blocked.
- Raw scraped videos are the primary content object.
- Selected/analyzed videos are statuses on raw videos, not the only records shown.
- Raw video records should include original TikTok URL, author handle, caption, hashtags, source input, engagement stats, weighted engagement rate, created date, Nattome relevance score, duplicate/noise flags, downloadable-video availability, selection/analyzed status, run ID, and config version.
- The MVP will use outbound TikTok links and metadata only.
- The MVP will not include embedded local video playback.
- Recommendations are passive insights.
- Recommendations can be marked accepted, ignored, or needs more data.
- Recommendations should link to supporting raw videos, runs, and source inputs.
- Recommendations can be resolved after underlying configuration changes.
- Marketers can directly edit production scrape settings.
- Edited settings affect the next scheduled run automatically.
- Settings edits use validated forms, not raw JSON editing.
- A JSON preview/export can exist later, but is not the main MVP control.
- Editable MVP settings are hashtags, keywords, competitor profiles, results per input, top N, daily selection size, scope, minimum views, maximum age days, minimum weighted engagement rate, requires downloadable video, and exclusion terms.
- Read-only MVP settings are API tokens, Apify actor ID, Gemini model, output paths, cleanup deletion settings, Telegram credentials, report schema, and scoring formula internals.
- Saving production settings requires a reason.
- Every settings save creates a config version.
- Config versions include changed_by, timestamp, old value, new value, reason, and the next scheduled run that will use the version.
- The dashboard should show the current production config version and the config version that the next scheduled run will use.
- The dashboard should support rollback to a previous config version.
- Marketers can trigger immediate manual runs.
- Manual runs are distinct from scheduled runs.
- Manual runs never overwrite existing scheduled deliverables.
- The dashboard will expose two manual run actions: Run scrape now and Run full pipeline.
- Run scrape now runs the scrape/discovery step for fast feedback.
- Run full pipeline runs scrape plus selection, evidence analysis, reports, workbook generation, and delivery behavior.
- Run actions should show estimated runtime and expected outputs before launch.
- Runs should be indexed after completion.
- Scheduled daily behavior should support scrape/discovery monitoring.
- Scheduled weekly behavior should support the full evidence pipeline and final deliverables.
- Run History optimizes trend monitoring first, with drill-down audit/debug detail.
- Run History should include quality score trends, candidate volume trends, eligibility yield trends, relevance trends, engagement trends, and config version overlays.
- Run drill-down should expose raw content, selected content, score drivers, pipeline phases, logs, and output links.
- Pattern Library and Nattome POV Library are dashboard features.
- Candidate Patterns are auto-generated from batch/run analysis.
- Approved Patterns are marketer-curated canonical entries.
- Pattern Library represents external TikTok mechanics.
- Nattome POV Library represents Nattome's owned brand-safe interpretations, marketing territories, and adaptation rules.
- Marketers can edit Approved Pattern Library entries.
- Marketers can edit Nattome POV Library entries.
- Architecture docs, tool decisions, PRDs, ADRs, raw artifacts, run outputs, and pipeline logs are read-only in MVP.
- Pattern and POV entries support optional product, campaign, market, language, audience/avatar, symptom/occasion, channel, status, and source links.
- Pattern and POV status values should include draft, approved, and archived.
- Default values can assume Nattome, Malaysia, and mixed/English language.
- Pipeline Architecture will include full architecture, tool stack, PRDs, ADRs, phase/status map, file/output map, and data lineage.
- Global search should cover raw videos, runs, Candidate Patterns, Approved Patterns, Nattome POVs, architecture docs, and reports.
- Search should include faceted filters rather than keyword search alone.
- MVP exports are filtered raw videos CSV, run summaries CSV, Approved Patterns Markdown, Nattome POVs Markdown, and links to existing reports/workbooks.
- A custom deck builder, custom report builder, hosted database, authentication, and local media playback are out of scope for MVP.

The main implementation modules are expected to be:

- an artifact indexer that reads repo artifacts and normalizes runs, raw videos, selected status, outputs, logs, and docs into dashboard records
- a dashboard SQLite storage layer that owns mutable state, versioning, libraries, and recommendations
- a Scrape Quality Score module that computes explainable scrape-only scores and quality drivers
- a Pipeline Health summarizer that converts run manifests, logs, and output existence into impact summaries and technical drill-downs
- a scrape settings validation and config versioning module that manages marketer-editable production settings and rollback
- a run orchestration module that launches scrape-only and full-pipeline manual runs without overwriting artifacts
- a recommendation engine that generates passive suggestions from score drivers
- a Pattern Library and Nattome POV Library module with versioned marketer editing
- a search and facet indexing module for runs, videos, libraries, reports, and architecture docs
- export handlers for CSV and Markdown exports
- frontend pages for Overview, Scraped Content, Run History, Scrape Settings, Recommendations, Pattern Library, Nattome POV Library, and Pipeline Architecture

## Testing Decisions

- Tests should validate external behavior through public module interfaces, database records, generated summaries, and UI-visible state, not private helper implementation details.
- The Scrape Quality Score module should be tested with representative run and scrape data.
- Scrape Quality tests should verify the score excludes claim safety, manual review burden, and evidence extraction success.
- Scrape Quality tests should verify the score dimensions and weighting produce expected strong, usable, and needs-attention bands.
- Scrape Quality tests should verify a score below 60 creates an attention condition but does not mutate settings.
- Artifact indexing tests should verify raw scrapes, selected batches, run manifests, pipeline health artifacts, reports, and output links normalize into stable dashboard records.
- Artifact indexing tests should verify raw scraped videos remain the primary records and selected/analyzed state is represented as status.
- Artifact indexing tests should verify the index can be rebuilt from artifacts without losing dashboard-owned config versions, approved patterns, or POV entries.
- SQLite storage tests should verify attribution fields, timestamps, version history, rollback data, and durable dashboard-owned records.
- Settings validation tests should verify hashtag normalization, profile normalization, duplicate detection, numeric threshold validation, scope validation, and required save reason behavior.
- Config versioning tests should verify each save records old values, new values, reason, user, timestamp, and active production version.
- Rollback tests should verify previous config versions can become active without losing history.
- Run orchestration tests should verify Run scrape now and Run full pipeline produce distinct manual run records and never overwrite scheduled artifacts.
- Pipeline Health tests should verify plain-language impact summaries for completed, partial, warning, error, and blocked phases.
- Pipeline Health tests should verify technical details remain available for expanded views.
- Recommendation tests should verify recommendations are generated from quality drivers without mutating settings.
- Recommendation tests should verify recommendations can be marked accepted, ignored, needs more data, and resolved.
- Pattern Library tests should verify Candidate Patterns can be promoted to Approved Patterns with version history.
- Nattome POV Library tests should verify marketer edits preserve version history and optional targeting fields.
- Search tests should verify keyword search plus facets return expected videos, runs, patterns, POVs, docs, and reports.
- Export tests should verify filtered videos and run summaries export to CSV, and approved patterns/POVs export to Markdown.
- UI or integration tests should focus on critical marketer workflows: opening Latest Run Overview, editing settings with validation, saving a config version, running a manual scrape, browsing raw videos, reviewing recommendations, viewing run trends, and editing approved pattern/POV entries.
- Prior art includes existing run manifest tests, Batch Analysis Run CLI tests, output rendering tests, cleanup tests, Telegram delivery tests, candidate selection tests, report generation tests, and structured JSON tests.

## Out of Scope

- Building the dashboard implementation in this PRD step.
- Replacing the existing Markdown reports, Excel workbooks, JSON outputs, run folders, skills, PRDs, or ADRs.
- Hosted multi-user deployment.
- Authentication, role-based permissions, or account management.
- Embedded local TikTok video playback.
- Downloaded video browsing or media gallery functionality.
- Direct editing of API keys, Apify actor ID, Gemini model, output paths, cleanup deletion settings, Telegram credentials, report schemas, or scoring formula internals.
- Automatic settings mutation from recommendations.
- Automatic settings mutation from low Scrape Quality Score.
- Full custom report builder.
- Presentation/deck generation.
- Direct social publishing workflow.
- Replacing the existing evidence-first Batch Analysis Run or Top 5 Creative Production Report pipeline.

## Further Notes

The dashboard should use the project's existing domain language: Batch Analysis Run, Run Folder, Batch Output Set, Minimum Eligibility Filter, Viral Relevance Selection, Evidence Bundle, Video Evidence Report, Cross-Video Pattern Summary, Scrape Quality Score, Pipeline Health, Pattern Library, and Nattome POV Library.

The dashboard should respect the existing evidence-first architecture. It should not imply that a raw scrape has been analyzed unless a corresponding Batch Analysis Run has selected and processed that video. It should clearly distinguish raw scrape metadata from selected/analyzed evidence outputs.

The dashboard should make the marketer's improvement loop explicit:

1. Review Latest Run Overview.
2. Inspect Scrape Quality Score and quality drivers.
3. Browse raw scraped videos.
4. Review passive recommendations.
5. Edit production scrape settings through validated forms.
6. Save a versioned config change with a reason.
7. Run scrape now for fast feedback or wait for the next scheduled run.
8. Monitor Run History trends against config versions.

The implementation should prefer deep modules with small interfaces for indexing, scoring, settings/versioning, run orchestration, recommendations, and library curation. Those modules should be testable without launching a browser or calling Apify/Gemini.
