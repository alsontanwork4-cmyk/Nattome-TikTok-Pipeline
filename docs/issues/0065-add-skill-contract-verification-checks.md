# Add Skill Contract Verification Checks

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Add lightweight verification for the Daily Evidence Run skill contract. The checks should verify observable documentation and skill behavior contracts rather than fragile exact paragraph wording.

The completed slice should catch regressions where the project again exposes multiple normal entry points, promotes metadata previews to production guidance, reintroduces weekly/default-batch language as the current normal workflow, or drops required evidence reporting fields.

## Acceptance criteria

- [ ] A verification check confirms the primary skill is user-facing for normal Daily Evidence Run operation.
- [ ] A verification check confirms the discovery phase skill is support-only or non-user-invocable.
- [ ] A verification check confirms the evidence-analysis phase skill is support-only or non-user-invocable.
- [ ] A verification check confirms current skill and high-level docs use Daily Evidence Run and Daily Top-5 Selection language.
- [ ] A verification check confirms current skill and high-level docs do not present weekly/default-batch/deep-run behavior as the normal operating path.
- [ ] A verification check confirms pre-Gemini discovery guidance uses candidate preview or metadata inference language.
- [ ] A verification check confirms the primary skill requires evidence status, final report path, planning workbook path, Run Folder path, Shootable Angles, Claim Safety Review risks, Manual Review Flags, and missing/failed evidence in reporting.
- [ ] A verification check confirms `config.example.json` parses as JSON.
- [ ] The verification is runnable with the repo's normal test command or a clearly documented focused command.
- [ ] The checks avoid depending on exact full paragraphs unless no more stable contract signal exists.

## Blocked by

- `docs/issues/0062-make-daily-evidence-run-the-primary-skill.md`
- `docs/issues/0063-reframe-phase-skills-as-supporting-references.md`
- `docs/issues/0064-align-docs-and-glossary-to-daily-top-5-operation.md`
