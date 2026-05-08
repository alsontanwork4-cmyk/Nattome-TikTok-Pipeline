# Make Daily Evidence Run The Primary Skill

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Update the primary Nattome skill so it is the clear normal entry point for the Daily Evidence Run. The skill should describe the end-to-end daily path: check credentials, run TikTok discovery, create the Daily Top-5 Selection handoff, run Gemini evidence analysis on those same videos, and report the final evidence-backed outputs.

The completed slice should make it obvious that normal operation is one daily workflow, not a choice between discovery, evidence analysis, and orchestration.

## Acceptance criteria

- [ ] `nattome-viral-intelligence-run` is the only skill described as the normal operation entry point.
- [ ] The primary skill uses Daily Evidence Run and Daily Top-5 Selection language.
- [ ] The primary skill includes required credential checks for discovery and Gemini evidence analysis.
- [ ] The primary skill includes the daily discovery command.
- [ ] The primary skill includes the daily `--mode daily` evidence analysis command.
- [ ] The primary skill lists the primary output paths: raw scrape, daily top-5 handoff, final Markdown report, Excel planning workbook, and Run Folder.
- [ ] The primary skill reporting checklist includes evidence status, top evidence-backed Shootable Angles, Nattome Priority Scores, Claim Safety Review risks, Manual Review Flags, and failed or missing evidence.
- [ ] The primary skill honesty rules forbid turning metadata-only reads into Shootable Angles.
- [ ] The primary skill points to shared brand, virality, and domain references instead of duplicating long reference content.

## Blocked by

None - can start immediately.
