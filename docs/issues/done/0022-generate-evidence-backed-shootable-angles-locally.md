# Generate Evidence-Backed Shootable Angles Locally

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Add a pure domain module that generates final Shootable Angles from candidate metadata and Evidence Bundle snapshots. Gemini supplies evidence only; Codex or Claude Code local logic owns avatar, product fit, claim guardrails, final angle shape, and Nattome Priority Score.

Each video may produce up to three evidence-backed Shootable Angles. Weak filler angles should not be generated.

## Acceptance Criteria

- [ ] Shootable Angle generation is a pure module that does not write files.
- [ ] Gemini evidence is treated as input only and does not become the final creative authority.
- [ ] Each video can produce zero, one, two, or three Shootable Angles depending on evidence strength.
- [ ] No video is forced to produce filler angles.
- [ ] Each Shootable Angle includes hook, avatar, format, product fit, recommendation, and claim guardrails.
- [ ] Nattome Priority Score keeps six dimensions and a 30-point maximum.
- [ ] The six score dimensions remain viral strength, Nattome relevance, evidence confidence, brand safety, ease of production, and product fit.
- [ ] Tests cover zero, one, and multiple evidence-backed angle outputs.
- [ ] Tests cover Nattome Priority Score calculation and claim guardrail handling.

## Blocked By

- `0021-render-video-evidence-reports-from-gemini-evidence-snapshots.md`
