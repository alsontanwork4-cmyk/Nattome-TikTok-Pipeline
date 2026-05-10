# Document Automation Prompt And Global Skill Sync

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Document the recommended automation prompt for scheduled Daily Evidence Runs and the process for syncing repo-local Nattome skills into the global Codex skills directory.

The completed slice should make the automation prompt reusable without relying on conversation history, and should make the repo-local skill folders the maintainable source for global Codex skill copies.

## Acceptance criteria

- [ ] The recommended Daily Evidence Run automation prompt is stored in a durable project document.
- [ ] The prompt explicitly triggers `nattome-viral-intelligence-run`.
- [ ] The prompt instructs the automation to run discovery and Gemini evidence analysis together.
- [ ] The prompt requires reporting raw scrape path, daily top-5 handoff path, final report path, planning workbook path, and Run Folder path.
- [ ] The prompt requires reporting Gemini evidence status for each video.
- [ ] The prompt requires reporting top evidence-backed Shootable Angles with Nattome Priority Scores.
- [ ] The prompt requires reporting Claim Safety Review risks, Manual Review Flags, failed downloads, and missing video evidence.
- [ ] The prompt forbids production-ready Shootable Angles from metadata alone.
- [ ] Documentation explains that repo-local skill folders are the source of truth.
- [ ] Documentation explains when and how to sync updated repo-local skills into global Codex skills.

## Blocked by

- `docs/issues/0062-make-daily-evidence-run-the-primary-skill.md`
- `docs/issues/0063-reframe-phase-skills-as-supporting-references.md`
- `docs/issues/0064-align-docs-and-glossary-to-daily-top-5-operation.md`
