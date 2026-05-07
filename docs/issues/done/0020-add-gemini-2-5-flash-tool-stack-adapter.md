# Add Gemini 2.5 Flash Tool Stack Adapter

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Add a Gemini 2.5 Flash Tool Stack Adapter that analyzes one source TikTok video and normalizes the response into timestamped Nattome evidence. Gemini should provide evidence for visual observations, visible text, spoken content, audio cues, first-three-second hook evidence, and claim evidence. Gemini must not generate final Shootable Angles.

Normal tests should use fake Gemini responses and must not require live Gemini calls.

## Acceptance Criteria

- [ ] Gemini 2.5 Flash is configurable as the primary Tool Stack Adapter.
- [ ] The adapter accepts one source video artifact and candidate context.
- [ ] The adapter normalizes Gemini output into timestamped Nattome evidence concepts.
- [ ] Normalized evidence includes visual observations, OCR-style visible text, spoken content, audio cues, hook evidence, and claim evidence when available.
- [ ] Gemini evidence is written through the Evidence Bundle Reader/Writer under the two-layer layout.
- [ ] Gemini failures and missing credentials are recorded honestly in the Run Manifest and evidence state.
- [ ] Gemini does not produce final Shootable Angles.
- [ ] Tests use fake Gemini responses for successful, partial, and failed evidence extraction.
- [ ] Normal test runs do not require network access or live Gemini credentials.

## Blocked By

- `0019-write-evidence-bundle-snapshots-in-two-layer-layout.md`
