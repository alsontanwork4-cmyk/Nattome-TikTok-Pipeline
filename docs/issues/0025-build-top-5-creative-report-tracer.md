# Build Top 5 Creative Report Tracer

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/top5-creative-production-report-prd.md`

## What To Build

Create the first end-to-end Markdown output path for the new Top 5 Creative Production Report.

This slice should write `top5_creative_production_report_YYYY-MM-DD.md` under `outputs/reports/YYYY-MM-DD/` for a completed run. The report should cover only the final top five selected videos, preserve pipeline selected rank order, open with "What We Learned From These 5 Videos", and render five production-focused creative briefs with source references, Inspiration Pattern, "Why This Works For Nattome Content", and a compact three-angle concept table.

This tracer does not need the full Recommended Shoot script table yet. It should establish the new report shape, data flow, final output location, and tests for the base report contract.

## Acceptance Criteria

- [ ] A completed run can write `outputs/reports/YYYY-MM-DD/top5_creative_production_report_YYYY-MM-DD.md`.
- [ ] The Markdown report includes only the final top five selected videos.
- [ ] The five creative briefs are ordered by pipeline selected rank.
- [ ] The report starts with "What We Learned From These 5 Videos".
- [ ] The opening section contains practical reusable creative lessons, not pipeline metadata.
- [ ] The report does not include a generic executive summary.
- [ ] The report does not include a top priority table.
- [ ] The report does not group briefs by product or marketing theme.
- [ ] The report does not include thumbnails or screenshots.
- [ ] Each brief title uses the recommended Nattome concept name when available.
- [ ] Each brief includes source creator, source video link, views, likes, comments, and shares.
- [ ] Each brief includes an Inspiration Pattern.
- [ ] Each brief includes "Why This Works For Nattome Content".
- [ ] Each brief includes a compact three-angle table with Concept, Hook, Format, and Why it works columns.
- [ ] The report does not include standalone original source hook or full caption fields.
- [ ] The report does not include a final claims guardrail bank.
- [ ] Focused tests cover the base report structure and absence of removed sections.

## Blocked By

None - can start immediately.
