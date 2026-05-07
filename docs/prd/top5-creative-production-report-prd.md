# Top 5 Creative Production Report PRD

## Problem Statement

The current Nattome TikTok pipeline produces several separate marketer-facing outputs: a Daily TikTok Brief, a Cross-Video Pattern Summary, and a CSV Spreadsheet Summary. Each output contains useful pieces, but the information is scattered across files and some sections are not useful for production decisions.

The Daily TikTok Brief is especially problematic because it can read like a daily intelligence report even when parts of its explanation are not grounded in full video evidence. The user does not want a metadata-led report that implies the system understands every frame, hook, and viral mechanism unless that evidence exists. The user wants the stronger parts of the current output preserved, especially the Nattome angle concepts and production usefulness, but consolidated into one clean marketer-facing report.

The marketing user already trusts the pipeline to filter and select the top five videos. The downstream output should not focus on discovery, ranking explanation, or broad research summaries. It should turn the selected viral videos into production-ready Nattome creative briefs that a marketer can use to plan and shoot their own TikTok videos.

## Solution

The pipeline will replace the current scattered final outputs with exactly two user-facing deliverables for a completed run:

- one Markdown report named `top5_creative_production_report_YYYY-MM-DD.md`
- one Excel workbook named `top5_angle_planning_sheet_YYYY-MM-DD.xlsx`

Both files will be placed together in a date-based final output folder:

- `outputs/reports/YYYY-MM-DD/`

The Markdown report will cover only the final top five selected videos, ordered by the pipeline's selected rank. It will start with a short practical section called "What We Learned From These 5 Videos", then provide five creative briefs. Each brief will be titled using the recommended Nattome concept name, not the original source topic.

Each creative brief will include a small source reference block with creator, source video link, views, likes, comments, and shares. It will then provide an "Inspiration Pattern" label, a short section called "Why This Works For Nattome Content", a compact table of three Nattome angle options, and exactly one "Recommended Shoot".

Only the recommended shoot receives a full production-ready script. The script will be a timed table with `Time`, `Scene`, `On-screen text`, and `Exact line` columns. The default script length will be 20-35 seconds unless the source format clearly needs longer. Script language will be natural Malaysian retail-friendly English, not medical-professional heavy and not overly Gen Z. Product mention, product appearance, CTA, and soft close decisions will depend on the adapted video format and concept; they will not be forced by template rules.

The Excel workbook will be a production planning comparison sheet with two sheets:

- `Angles`: 15 rows, one per Nattome angle
- `Source Videos`: 5 rows, one per selected source video

The Excel workbook will preserve planning and scoring fields such as priority score and evidence quality. Full scripts will live only in the Markdown report.

The pipeline will stop writing the old final visible outputs once the new report is implemented:

- `daily_brief_YYYY-MM-DD.md`
- `cross_video_pattern_summary.md`
- `spreadsheet_summary.csv`

The pipeline may continue computing structured intermediate data internally when needed, but those old Markdown/CSV files should no longer be final marketer-facing deliverables.

## User Stories

1. As a Nattome marketer, I want one consolidated production report, so that I do not need to open multiple Markdown files to understand what to shoot.
2. As a Nattome marketer, I want the final report to cover only the selected top five videos, so that I can focus on the videos the pipeline already chose.
3. As a Nattome marketer, I want the top five briefs ordered by pipeline rank, so that the report preserves the pipeline's selection priority without adding another ranking table.
4. As a Nattome marketer, I want the report to start with practical lessons from the five videos, so that I can quickly understand reusable creative patterns.
5. As a Nattome marketer, I do not want a generic executive summary, so that the report does not feel like another daily briefing document.
6. As a Nattome marketer, I want each brief title to use the recommended Nattome concept name, so that the report feels like a production document rather than a research report.
7. As a Nattome marketer, I want each brief to include the source creator, source link, and engagement stats, so that I can refer back to the original viral video when needed.
8. As a Nattome marketer, I want each brief to include an Inspiration Pattern, so that I understand what kind of viral mechanic is being adapted.
9. As a Nattome marketer, I want each brief to explain why the pattern works for Nattome content, so that the adaptation logic is clear.
10. As a Nattome marketer, I want the explanation to be production-focused, so that it helps me make videos rather than study TikTok theory.
11. As a Nattome marketer, I want each source video to produce three Nattome concept options, so that I have enough creative alternatives for campaign planning.
12. As a Nattome marketer, I want the three concept options shown in a compact table, so that I can scan them quickly.
13. As a Nattome marketer, I want the concept table to show concept name, hook, format, and why it works, so that every alternate angle remains useful without creating clutter.
14. As a Nattome marketer, I want exactly one Recommended Shoot per brief, so that the report gives clear production direction.
15. As a Nattome marketer, I want the Recommended Shoot to include a one-sentence reason, so that I know why that concept was chosen.
16. As a Nattome marketer, I want only the Recommended Shoot to receive a full script, so that the report does not become 15 full scripts.
17. As a Nattome marketer, I want the full script to be shot-by-shot with exact suggested lines, so that the creator can film with minimal rewriting.
18. As a Nattome marketer, I want the script to include timing, so that the pacing is appropriate for TikTok.
19. As a Nattome marketer, I want the script table to include short on-screen text for every timed segment, so that the video can be planned for visual-first viewing.
20. As a Nattome marketer, I want script scenes to stay simple, so that the report does not become a detailed B-roll planning document.
21. As a Nattome marketer, I want scripts written in natural Malaysian retail-friendly English, so that they sound usable for local consumer content.
22. As a Nattome marketer, I do not want the scripts to sound overly medical, so that the videos stay accessible and native to TikTok.
23. As a Nattome marketer, I do not want the scripts to sound overly Gen Z, so that they fit Nattome's retail health context.
24. As a Nattome marketer, I want product mention to depend on the video format, so that the concept does not feel like a forced advertisement.
25. As a Nattome marketer, I want product appearance to happen only when natural, so that the first seconds can still focus on the viewer's problem or routine.
26. As a Nattome marketer, I want CTA usage to depend on the concept, so that educational or routine videos can end with a soft close when that is more natural.
27. As a Nattome marketer, I do not want hard CTA rules, so that the script can follow the creative format instead of the template.
28. As a Nattome marketer, I do not want source thumbnails or screenshots in the report, so that the report stays clean and source-linked.
29. As a Nattome marketer, I do not want original source hook or full caption text repeated in each brief, so that the report focuses on inspiration and Nattome adaptation.
30. As a Nattome marketer, I do not want a final claims guardrail bank, so that the report does not become a compliance document.
31. As a Nattome marketer, I want claim safety handled only where relevant, so that risky viral source claims are softened without adding recurring boilerplate.
32. As a Nattome marketer, I want the old daily brief removed, so that the pipeline no longer outputs a metadata-led report as if it were a full evidence analysis.
33. As a Nattome marketer, I want the old cross-video Markdown summary removed as a final output, so that broad pattern comparison does not compete with the production report.
34. As a Nattome marketer, I want the old CSV summary replaced by an Excel workbook, so that the planning sheet is easier to use in Excel.
35. As a Nattome marketer, I want the Excel workbook to include one row per Nattome angle, so that I can filter and sort the 15 concepts.
36. As a Nattome marketer, I want the Excel workbook to mark which angle is the recommended shoot, so that planning and production decisions are visible in the sheet.
37. As a Nattome marketer, I want the Excel workbook to include a Source Videos sheet, so that I can compare the five selected videos without repeating all angle details.
38. As a Nattome marketer, I want the Excel workbook to include priority score and evidence quality, so that operational confidence remains available outside the clean report.
39. As a Nattome marketer, I do not want full scripts in Excel, so that the workbook remains useful for planning and comparison.
40. As a Codex user, I want both final files placed together in one date-based folder, so that final deliverables are easy to find.
41. As a Codex user, I want the run folder to keep internal artifacts if needed, so that the pipeline can remain debuggable without exposing scattered final outputs.
42. As a maintainer, I want old final output registration updated, so that run manifests, batch indexes, delivery, and cleanup do not point users to removed deliverables.
43. As a maintainer, I want output rendering separated from output registration, so that the new report and workbook can be tested independently.
44. As a maintainer, I want script generation rules to live in a testable domain module, so that tone, table shape, recommended shoot selection, and optional CTA behavior can be validated without running the full pipeline.
45. As a maintainer, I want the new workbook writer to have a narrow interface, so that CSV replacement does not leak spreadsheet formatting concerns through the rest of the pipeline.
46. As a maintainer, I want existing structured JSON to remain available internally if required, so that downstream automation and debugging are not broken by removing old visible files.
47. As a maintainer, I want the new outputs to preserve Evidence-First Analysis, so that creative recommendations do not fabricate observed video details.
48. As a maintainer, I want the report to avoid unsupported frame-by-frame claims when evidence is missing, so that the final output is honest about what the pipeline knows.
49. As an automation runner, I want the final output paths to be predictable, so that scheduled runs and delivery integrations can reference the new report folder.
50. As an automation runner, I want removed outputs to disappear from final delivery messages, so that users are not sent obsolete file references.

## Implementation Decisions

- The feature will replace the current scattered marketer-facing output set with a single top-five creative production report and one Excel planning workbook.
- The Markdown report will be the primary marketer-facing creative document.
- The Excel workbook will be the production planning comparison document.
- The final user-facing output folder will be date-based under a stable reports output root.
- The report filename will be `top5_creative_production_report_YYYY-MM-DD.md`.
- The workbook filename will be `top5_angle_planning_sheet_YYYY-MM-DD.xlsx`.
- The report will include only the final top five selected videos.
- The report will preserve the pipeline selected order/rank.
- The report will not group by product or marketing theme.
- The report will not include a priority table at the top.
- The report will not include a generic executive summary.
- The report will not include thumbnails or screenshots.
- The report will not include a final claims guardrail bank.
- The report will not repeat the original source hook or full caption as a standalone field.
- The report will open with "What We Learned From These 5 Videos".
- The opening section will contain practical reusable creative lessons, not pipeline metadata.
- Each creative brief will use the recommended Nattome concept name as the section title.
- Each creative brief will include the source creator, source video link, views, likes, comments, and shares.
- Each creative brief will include an Inspiration Pattern label.
- Each creative brief will include "Why This Works For Nattome Content".
- Each creative brief will include a compact three-row concept table.
- The concept table columns will be Concept, Hook, Format, and Why it works.
- Each creative brief will have exactly one Recommended Shoot.
- The Recommended Shoot will include a one-sentence "Recommended because" explanation.
- The Recommended Shoot will include a separate Hook line.
- Only the Recommended Shoot will include a full script.
- The full script table columns will be Time, Scene, On-screen text, and Exact line.
- Recommended scripts will default to 20-35 seconds unless the source format clearly needs longer.
- Script lines will use natural Malaysian retail-friendly English.
- Script lines will avoid overly medical language.
- Script lines will avoid overly Gen Z language.
- Product mention will be concept-specific rather than mandatory.
- Product appearance will be concept-specific rather than mandatory.
- CTA usage will be concept-specific rather than mandatory.
- Soft closes will be allowed when a CTA would feel forced.
- Claim safety will be handled only inside the relevant brief language when needed.
- The Excel workbook will contain an Angles sheet and a Source Videos sheet.
- The Angles sheet will contain 15 rows, one per Nattome angle.
- The Source Videos sheet will contain 5 rows, one per selected source video.
- The Angles sheet will include a recommended shoot marker.
- The workbook will include planning/scoring fields including priority score and evidence quality.
- Full scripts will not be written into the workbook.
- The old daily brief should stop being written as a final visible output.
- The old cross-video Markdown summary should stop being written as a final visible output.
- The old spreadsheet CSV should stop being written as a final visible output.
- Existing internal structured data may continue to be generated where needed.
- Run manifest output registration should reference the new report and workbook.
- Batch index rendering should reference the new report and workbook.
- Telegram delivery messaging should reference the new report and workbook if delivery remains enabled.
- Cleanup preservation rules should preserve the new final report and workbook.
- Documentation and skill instructions should be updated so users no longer expect the old three-output shape.

The main implementation modules are expected to be:

- a creative production report renderer for the final top-five Markdown report
- a planning workbook writer for the two-sheet Excel workbook
- a structured report view/model that converts selected videos and shootable angles into report-ready data
- output registration changes for run manifest and batch index generation
- delivery and cleanup updates for the new final output set
- documentation and skill instruction updates for the new workflow

## Testing Decisions

- Tests should validate external behavior through generated files and structured output records, not private helper implementation details.
- The report renderer should have focused tests proving the expected top-level headings, brief order, source block, Inspiration Pattern, Nattome-focused explanation, three-angle table, Recommended Shoot marker, hook line, and timed script table.
- Report renderer tests should prove that only the recommended shoot receives a full script.
- Report renderer tests should prove that no executive summary, priority table, thumbnails, source hook field, or final claims guardrail bank is rendered.
- Report renderer tests should cover optional CTA behavior by checking that scripts can end with either a CTA or a soft close depending on the input concept.
- Workbook writer tests should verify the workbook has exactly two sheets named Angles and Source Videos.
- Workbook writer tests should verify the Angles sheet has one row per angle and marks exactly one recommended shoot per source video.
- Workbook writer tests should verify the Source Videos sheet has one row per selected video.
- Workbook writer tests should verify priority score and evidence quality are included.
- Workbook writer tests should verify full scripts are not included in workbook cells.
- Output registration tests should verify the final output folder and filenames are date-based and stable.
- Output registration tests should verify old final visible output paths are no longer registered for new runs.
- Batch index tests should verify the new report and workbook are listed instead of the old Cross-Video Pattern Summary and CSV spreadsheet.
- Telegram delivery tests should verify delivery messages point to the new final outputs when delivery is enabled.
- Cleanup tests should verify the new final report and workbook are preserved.
- CLI-scale regression tests should verify a completed Batch Analysis Run produces the new final output pair.
- CLI-scale regression tests should verify new runs do not write the old final visible Markdown and CSV files.
- Existing tests around evidence extraction, evidence quality, claim safety, and structured JSON should remain focused on evidence correctness rather than report formatting.
- Prior art includes the existing batch output tests, full Batch Analysis Run CLI tests, run manifest tests, batch index tests, cleanup tests, Telegram delivery tests, and output rendering tests.

## Out of Scope

- Implementing code changes is out of scope for this PRD document itself.
- Changing the top-five selection algorithm is out of scope.
- Changing Minimum Eligibility Filter thresholds is out of scope.
- Changing Gemini evidence extraction behavior is out of scope.
- Adding frame-by-frame AI analysis beyond the existing Evidence-First Analysis pipeline is out of scope.
- Generating thumbnails or screenshots in the final Markdown report is out of scope.
- Producing full scripts for all 15 angles is out of scope.
- Adding a product/theme grouping system to the Markdown report is out of scope.
- Maintaining the old Daily TikTok Brief as a final visible output is out of scope.
- Maintaining the old Cross-Video Pattern Summary as a final visible Markdown output is out of scope.
- Maintaining the old CSV Spreadsheet Summary as a final visible output is out of scope.
- Uploading reports to external storage is out of scope.
- Creating a web UI for report browsing is out of scope.
- Changing scheduled run cadence is out of scope.
- Changing Telegram destination configuration is out of scope.
- Migrating or deleting historical output files is out of scope.

## Further Notes

- The new output design changes the marketer-facing shape of the Batch Output Set, but it should preserve the spirit of Evidence-First Analysis.
- The report should never imply that the pipeline watched or understood a video frame-by-frame unless the relevant evidence exists.
- The user wants the good concepts from the current Daily TikTok Brief preserved, especially Nattome angle generation and production usefulness.
- The user does not want the final output to feel like a metadata-led daily briefing.
- The product labels DR, DH, and DH-R should not drive report grouping because the user wants the products treated as one Nattome digestive-care family for marketer-facing purposes.
- Any retained internal structured output should serve pipeline reliability and automation, not create extra visible deliverables for the marketer.
