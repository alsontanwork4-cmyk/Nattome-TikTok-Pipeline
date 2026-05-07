# Write Evidence Bundle Snapshots In The Two-Layer Layout

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Add an Evidence Bundle Reader/Writer that owns two-layer file naming, stable per-video prefixes, artifact lookup, validation, and snapshot loading. Selected candidates with source videos should produce prefixed source metadata, source video state, and Evidence Bundle snapshot data under the new Run Folder layout.

This slice gives downstream modules one deep interface for reading a video's evidence state without manually assembling file paths.

## Acceptance Criteria

- [ ] Per-video files use a stable prefix made from rank and candidate ID.
- [ ] Source metadata and source video artifacts are written under the new two-layer layout.
- [ ] The Evidence Bundle Reader/Writer owns all file naming and artifact lookup.
- [ ] The Evidence Bundle Reader/Writer exposes one Evidence Bundle snapshot per selected video.
- [ ] Evidence Bundle snapshots include explicit missing-artifact states.
- [ ] Downstream callers can request a snapshot without knowing artifact filenames.
- [ ] Tests cover prefix generation, file placement, snapshot loading, and missing-artifact states.
- [ ] Tests verify that this slice does not create nested per-video folders.

## Blocked By

- `0018-create-two-layer-run-folder-and-run-manifest-skeleton.md`
