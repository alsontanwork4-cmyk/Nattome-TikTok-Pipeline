# Download Video Evidence Bundles

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

For each selected TikTok, create a per-video Evidence Bundle folder and download the source video as an Evidence Artifact. Preserve metadata and source references so each later report can be audited.

## Acceptance Criteria

- [ ] Each selected video gets a per-video folder inside the Run Folder.
- [ ] Each per-video folder stores metadata for the source TikTok.
- [ ] Each per-video folder stores the downloaded video when available.
- [ ] Download failures are captured clearly and do not produce fake evidence.
- [ ] The Evidence Bundle index records which artifacts exist for each video.
- [ ] Original TikTok links are preserved.

## Blocked By

- `0002-select-default-batch-with-minimum-eligibility-filter.md`
