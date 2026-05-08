# Daily Evidence Run Skill Consolidation PRD

## Problem Statement

The user wants the Nattome TikTok pipeline to be easy to run as a normal daily automation. The project previously exposed three skills in a way that made discovery, evidence analysis, and end-to-end orchestration look like equal alternatives. That created ambiguity: a user or scheduled automation could accidentally run only one phase, treat metadata previews as production insight, or follow old weekly/default-batch language that no longer matches the desired operating model.

The user's intended workflow is simpler. Normal operation should mean one Daily Evidence Run: discover TikTok candidates, create the Daily Top-5 Selection, run Gemini evidence analysis on those same five videos, and report the final evidence-backed Nattome outputs. Discovery-only and evidence-only behavior should remain available only for debugging or reruns, not as normal user-facing entry points.

The user also wants the skills to stay lean. Brand voice, virality taxonomy, domain language, claim guardrails, and report vocabulary should live in the shared reference documents and glossary instead of being copied across multiple skill files where they can drift.

## Solution

The project will formalize a one-skill normal operating model for the Nattome Daily Evidence Run.

The primary user-facing skill will be the Daily Evidence Run orchestrator. It will describe the full daily workflow, required credentials, daily commands, primary output expectations, reporting checklist, and honesty rules. It will be the only skill intended to trigger for normal automation prompts such as "run the Nattome pipeline for today."

The discovery and evidence-analysis phase skills will remain in place as supporting references. They will not be treated as normal alternatives. Discovery will own scraper configuration, scraper assets, and candidate preview rules. Evidence analysis will own evidence-only rerun/debug guidance for an existing daily candidate handoff. Both will explicitly point users back to the primary Daily Evidence Run skill for normal operation.

The canonical operating model will be daily top-5 only. User-facing weekly, default-batch, deep-run, and oversized-batch language will be removed from current skills and high-level project docs. Existing implementation names may remain where changing them would be unnecessary churn, but user-facing language should call the workflow a Daily Evidence Run and the selected set a Daily Top-5 Selection.

The source of truth for Nattome brand voice, virality analysis, and domain terminology will remain in the shared references and glossary. Skills will link to those sources and avoid duplicating long brand, avatar, claim, or virality sections.

The automation prompt will trigger the primary skill, run discovery and evidence analysis together, and require final reporting of evidence status, final report paths, planning workbook path, Run Folder path, top evidence-backed Shootable Angles, Claim Safety Review risks, Manual Review Flags, and missing/failed evidence.

## User Stories

1. As a Nattome operator, I want one normal skill for the daily pipeline, so that I do not need to decide between three similar skills.
2. As a Nattome operator, I want the normal skill to run discovery and evidence analysis together, so that I do not accidentally stop at a metadata-only handoff.
3. As a Nattome operator, I want the normal workflow to use the Daily Top-5 Selection, so that the run stays focused on the five most useful candidates.
4. As a Nattome operator, I want the automation prompt to trigger the primary skill, so that scheduled runs follow the same workflow every day.
5. As a Nattome operator, I want discovery-only behavior to remain available for debugging, so that I can troubleshoot scraper inputs without paying for or waiting on Gemini analysis.
6. As a Nattome operator, I want evidence-only behavior to remain available for reruns, so that I can reprocess an existing daily handoff without scraping TikTok again.
7. As a Nattome marketer, I want the final daily outputs to be evidence-backed, so that production decisions are not based on captions and engagement metadata alone.
8. As a Nattome marketer, I want the final report and planning workbook to be the primary outputs, so that I know where to look after a completed run.
9. As a Nattome marketer, I want the optional discovery brief treated as a handoff or preview, so that I do not mistake it for the final production report.
10. As a Nattome marketer, I want the system to preserve Gemini evidence statuses exactly, so that I can tell whether a video was completed, partial, missing credentials, missing, or failed.
11. As a Nattome marketer, I want missing or weak evidence surfaced clearly, so that I know which videos require manual review.
12. As a Nattome marketer, I want metadata-only observations labeled as candidate previews, so that unsupported reads do not become production recommendations.
13. As a Nattome marketer, I want the term Shootable Angle reserved for evidence-backed recommendations, so that creative planning stays grounded in source-video evidence.
14. As a Nattome marketer, I want Claim Safety Review risks reported after each run, so that viral health claims are not copied directly into Nattome content.
15. As a Nattome marketer, I want Manual Review Flags reported after each run, so that uncertain OCR, transcript, hook, language, audio, or claim evidence is not hidden.
16. As a Nattome marketer, I want high-view but weak-engagement videos called out honestly, so that paid-push or bait signals are not mistaken for good creative models.
17. As a Nattome marketer, I want the top evidence-backed Shootable Angles summarized with Nattome Priority Scores, so that I can quickly decide what to shoot first.
18. As a Nattome marketer, I want the Daily Evidence Run to use the existing Nattome brand voice reference, so that outputs remain warm, practical, Malaysian, clinically backed, and claim-safe.
19. As a Nattome marketer, I want the virality analysis lens to live in one reference, so that hook, pacing, structure, emotional trigger, and "why this won" language stays consistent.
20. As a maintainer, I want the phase skills to be supporting references, so that their useful debugging knowledge remains available without competing with the primary skill.
21. As a maintainer, I want the primary skill to stay concise, so that it is easy to audit and unlikely to drift from implementation behavior.
22. As a maintainer, I want long brand and virality guidance removed from duplicated skill bodies, so that updates happen in one place.
23. As a maintainer, I want the glossary to use Daily Evidence Run and Daily Top-5 Selection, so that project language matches the current operating model.
24. As a maintainer, I want high-level docs to remove old weekly/default-batch wording, so that new contributors do not copy obsolete behavior into prompts or code.
25. As a maintainer, I want existing implementation names preserved when harmless, so that documentation cleanup does not force unnecessary code churn.
26. As a maintainer, I want the local repo skills and global Codex skills to be syncable, so that the same operating model is available inside and outside this repository.
27. As a maintainer, I want supporting skill metadata to indicate they are not user-invocable, so that tool selection favors the primary Daily Evidence Run.
28. As a maintainer, I want the discovery support skill to own candidate preview rules, so that pre-Gemini language remains explicitly limited.
29. As a maintainer, I want the evidence support skill to own evidence-only rerun rules, so that reruns preserve the same output and honesty expectations as the main workflow.
30. As a maintainer, I want the automation prompt to list required report fields, so that daily scheduled output is consistently useful.
31. As a maintainer, I want tests or verification to focus on external behavior of skill text and docs, so that implementation details do not make documentation tests brittle.
32. As a future agent, I want one clear skill entry point, so that I can run the Nattome pipeline correctly without re-interviewing the user.

## Implementation Decisions

- The primary user-facing workflow is the Daily Evidence Run.
- Normal operation means discovery plus Gemini evidence analysis in one workflow.
- The selected daily set is the Daily Top-5 Selection.
- Discovery-only and evidence-only workflows are retained as supporting references for debugging and reruns.
- Supporting phase skills are not normal user entry points.
- The primary skill owns the daily workflow contract: credential checks, discovery command, daily evidence command, primary outputs, reporting checklist, and honesty rules.
- The discovery support skill owns scraper configuration guidance, candidate handoff outputs, candidate preview rules, and the rule that pre-Gemini reads are metadata inferences.
- The evidence support skill owns daily evidence rerun guidance, Run Manifest/output expectations, evidence status reporting, Manual Review Flags, and Claim Safety Review reporting.
- Brand voice, avatars, product positioning, claim guardrails, and virality taxonomy remain in shared reference documents rather than being copied into each skill.
- Domain language is grounded in the project glossary, especially Daily Evidence Run, Daily Top-5 Selection, Evidence Bundle, Video Evidence Report, Claim Safety Review, Evidence Quality Score, Manual Review Flag, Shootable Angle, and Nattome Priority Score.
- User-facing weekly/default-batch/deep-run language is removed from current skills and top-level docs.
- Existing implementation names that are already wired into scripts, packages, or folders can remain unless there is a separate reason to rename them.
- The optional discovery markdown remains a preview or handoff artifact, not the final production report.
- The final marketer-facing outputs remain the Top 5 Creative Production Report and the Excel planning workbook.
- The automation prompt must trigger the primary skill and require exact evidence-status reporting.
- Metadata-only observations must use preview language and cannot be promoted to Shootable Angles.
- The global Codex skill copy should be treated as a deployment target for the repo-local skill source of truth.

## Testing Decisions

- Good tests should verify observable behavior of the skill and documentation contracts, not internal wording choices.
- Tests should check that the primary skill is the only normal user-invocable skill.
- Tests should check that the discovery and evidence support skills are marked as supporting or non-user-invocable.
- Tests should check that current skill and high-level docs use Daily Evidence Run and Daily Top-5 Selection as the normal operating language.
- Tests should check that current skill and high-level docs do not reintroduce weekly/default-batch/deep-run language as a normal path.
- Tests should check that the discovery config example remains valid JSON after documentation edits.
- Tests should check that the automation prompt contract includes the final report, planning workbook, Run Folder, evidence status, Shootable Angles, Claim Safety Review risks, Manual Review Flags, and failed/missing evidence.
- Prior art exists in the repository for documentation contract verification and issue-level acceptance criteria. Similar lightweight checks should be preferred over tests that depend on exact paragraphs.
- Runtime pipeline tests are not required for documentation-only skill consolidation unless command behavior changes.

## Out of Scope

- Renaming existing packages, scripts, CLI flags, folders, or run roots.
- Changing TikTok scraping behavior.
- Changing Gemini evidence extraction behavior.
- Changing selection scoring, Minimum Eligibility Filter thresholds, or Daily Top-5 Selection logic.
- Changing report generation, workbook generation, evidence quality scoring, or claim safety logic.
- Removing phase folders that own real scripts, assets, or reference material.
- Building a new scheduler or automation runner.
- Creating new brand voice or virality framework content beyond pointing skills to the existing references.
- Rewriting historical completed issues or old PRDs that describe prior architecture decisions.

## Further Notes

- This PRD captures the decisions from the skill refinement session: optimize for normal operation, keep one primary user-facing skill, make phase skills supporting references, use daily top-5 only, avoid duplicated brand/virality prose, keep the discovery brief optional, and reserve Shootable Angle language for Gemini-backed evidence.
- The user explicitly prefers the Daily Evidence Run over weekly analysis.
- The repo-local skill files should be treated as the maintainable source. Global Codex skills may be synced from them when the user wants the same behavior outside this repository.
