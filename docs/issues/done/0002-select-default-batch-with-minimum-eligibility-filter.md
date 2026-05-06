# Select Default Batch With Minimum Eligibility Filter

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Add candidate ingestion and selection for a Default Batch. The slice should apply the Minimum Eligibility Filter first, then Viral Relevance Selection, and write a selected batch preview into the Run Folder.

## Acceptance Criteria

- [ ] The run can ingest TikTok candidate metadata from Apify output or an equivalent local fixture.
- [ ] Candidates under 10,000 views are excluded by default.
- [ ] Candidates older than 30 days are excluded by default.
- [ ] Candidates below 3% weighted engagement are excluded by default.
- [ ] Candidates without a usable TikTok link are excluded.
- [ ] Selection ranks remaining candidates by virality, recency, and Nattome relevance.
- [ ] The selected batch is written as JSON and markdown preview in the Run Folder.

## Blocked By

- `0001-create-batch-analysis-run-skeleton.md`
