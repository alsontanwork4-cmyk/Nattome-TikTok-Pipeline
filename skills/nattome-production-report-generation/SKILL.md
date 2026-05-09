---
name: nattome-production-report-generation
description: Human and agent reference for generating evidence-qualified Nattome production reports and manual single-video analyses. Use when shaping final production report content, workbook fields, or manual evidence-first review from a user-provided TikTok link or video.
user-invocable: false
---

# Nattome Production Report Generation

This is a workflow reference. Python owns deterministic orchestration, candidate qualification, structured JSON, workbook creation, manifest/cloud/Telegram state, and no-output behavior.

## Production Run Report Workflow

1. Analyze the Daily Top-3 Selection first.
2. Analyze up to two backfill candidates only when a Top-3 candidate does not qualify.
3. Treat a candidate as production-qualified only when it has at least one evidence-backed Shootable Angle generated from source-video evidence.
4. Write production report and workbook files only for production-qualified candidates.
5. Skip production report and workbook files entirely when zero candidates qualify.

## Manual Single-Video Analysis Workflow

1. Accept a user-provided TikTok link or source video.
2. Capture or verify source-video evidence before production recommendations.
3. Produce candidate preview or manual-review notes when source-video evidence is unavailable.
4. Generate Shootable Angles only after evidence supports the hook, structure, pacing, emotional trigger, and claim-safety read.
5. Produce exactly one timed Recommended Shoot for the strongest evidence-backed angle.

## Evidence-First Analysis

Both workflows must cite source-video evidence before making production claims. metadata-only analysis may produce candidate previews and manual-review notes only. It must never produce Shootable Angles, Recommended Shoots, Nattome Priority Scores, or production recommendations.

## Claim Safety Review

Run Claim Safety Review before any Nattome adaptation. Do not reuse source claims that imply cure, guaranteed relief, medical outcomes, detox, overnight transformation, or unsupported clinical claims. Carry claim guardrails into every Shootable Angle and the Recommended Shoot.

## Production Report Headings

Use these exact Markdown headings per production-qualified video:

- `## <N>. <Concept Name>`
- `### Source Reference`
- `### Inspiration Pattern`
- `### Why This Works For Nattome Content`
- `### Recommended Shoot`

Report sections are numbered `1..N` for production-qualified videos. Keep the source selection rank visible inside `### Source Reference`.

## Workbook Tabs

The workbook has two tabs:

- `Angles` - one row per evidence-backed Shootable Angle, including source rank, source ID, creator, source link, metrics, concept, hook, format, why it works, Recommended Shoot marker, priority score dimensions, evidence quality, and manual review fields.
- `Source Videos` - one row per production-qualified source video, including source rank, source ID, creator, source link, caption, metrics, evidence quality, manual review fields, recommended concept, hook, product fit, and priority score.

## Recommended Shoot Rule

Each production-qualified video gets exactly one timed Recommended Shoot. Use the top evidence-backed angle for that video. Do not create additional full scripts for secondary angles.
