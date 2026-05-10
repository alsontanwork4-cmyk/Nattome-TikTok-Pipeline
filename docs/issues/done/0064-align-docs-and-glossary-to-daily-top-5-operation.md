# Align Docs And Glossary To Daily Top-5 Operation

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0061-formalize-daily-evidence-run-skill-consolidation.md`

## What to build

Update high-level project documentation and glossary language so the current operating model is daily top-5 only. README and glossary language should teach Daily Evidence Run and Daily Top-5 Selection as the normal workflow, while keeping existing implementation names only where they describe current scripts, packages, or folders.

The completed slice should prevent future agents and contributors from reintroducing weekly/default-batch assumptions into prompts or docs.

## Acceptance criteria

- [ ] README describes normal operation as a Daily Evidence Run.
- [ ] README says the Daily Evidence Run uses a Daily Top-5 Selection.
- [ ] README describes the discovery brief as optional preview or handoff output, not the final production report.
- [ ] README identifies the Top 5 Creative Production Report and Excel planning workbook as the primary marketer-facing outputs.
- [ ] `CONTEXT.md` defines Daily Evidence Run.
- [ ] `CONTEXT.md` defines Daily Top-5 Selection.
- [ ] `CONTEXT.md` relationships use daily terminology for the current normal workflow.
- [ ] Current README and glossary language do not present weekly/default-batch/deep-run behavior as the normal path.
- [ ] `config.example.json` remains valid JSON after wording changes.
- [ ] Existing implementation names are not renamed unless required for clarity.

## Blocked by

- `docs/issues/0062-make-daily-evidence-run-the-primary-skill.md`
