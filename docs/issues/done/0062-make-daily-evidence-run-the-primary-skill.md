# Make Daily Evidence Run The Primary Skill

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Update the primary Nattome skill so it is the clear normal entry point for the Daily Evidence Run. The skill should describe the end-to-end daily path: check credentials, run TikTok discovery, create the Daily Top-5 Selection handoff, run Gemini evidence analysis on those same videos, and report the final evidence-backed outputs.

The completed slice should make it obvious that normal operation is one daily workflow, not a choice between discovery, evidence analysis, and orchestration.

## Acceptance criteria

- [x] `nattome-viral-intelligence-run` is the only skill described as the normal operation entry point.
- [x] The primary skill uses Daily Evidence Run and Daily Top-5 Selection language.
- [x] The primary skill includes required credential checks for discovery and Gemini evidence analysis.
- [x] The primary skill includes the daily discovery command.
- [x] The primary skill includes the daily `--mode daily` evidence analysis command.
- [x] The primary skill lists the primary output paths: raw scrape, daily top-5 handoff, final Markdown report, Excel planning workbook, and Run Folder.
- [x] The primary skill reporting checklist includes evidence status, top evidence-backed Shootable Angles, Nattome Priority Scores, Claim Safety Review risks, Manual Review Flags, and failed or missing evidence.
- [x] The primary skill honesty rules forbid turning metadata-only reads into Shootable Angles.
- [x] The primary skill points to shared brand, virality, and domain references instead of duplicating long reference content.

## Blocked by

None - can start immediately.

## Completion notes

- Renamed the repo-local primary skill folder to `skills/nattome-viral-intelligence-run/`.
- Updated the primary skill metadata to `name: nattome-viral-intelligence-run`.
- Updated README references so the normal operation entry point matches the phase-skill guidance.
- Added a focused skill contract test for the primary skill name, commands, outputs, reporting checklist, honesty rule, and shared reference links.
