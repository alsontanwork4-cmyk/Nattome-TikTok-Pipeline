# Create Two-Layer Run Folder And Run Manifest Skeleton

Labels: needs-triage
Type: AFK

## Parent

`docs/prd/gemini-two-layer-evidence-pipeline-architecture-prd.md`

## What To Build

Create the new Run Folder skeleton for Batch Analysis Runs using only two folder layers. New runs should create direct child folders for reports, data, evidence, and logs, write an incremental `run_manifest.json`, and generate `batch_index.md` from that manifest.

This slice establishes the new Run Folder and Run Manifest shape before downstream evidence and output writers move onto it.

## Acceptance Criteria

- [ ] New Batch Analysis Runs create direct child folders for reports, data, evidence, and logs.
- [ ] New Batch Analysis Runs do not create nested batch output or evidence bundle folders.
- [ ] New Batch Analysis Runs write `run_manifest.json`.
- [ ] The Run Manifest includes configuration, run timestamp, mode, requested batch size, and initial phase records.
- [ ] Phase records are structured records, not derived booleans.
- [ ] `batch_index.md` is generated from `run_manifest.json`.
- [ ] Tests verify that no new run output path exceeds the Run Folder plus one direct child folder.
- [ ] Tests verify that skeleton runs still provide a human-readable batch index.

## Blocked By

- None - can start immediately
