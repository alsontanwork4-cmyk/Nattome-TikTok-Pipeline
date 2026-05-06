# Add Claim Safety Review

Type: AFK

## Parent

`docs/prd/nattome-tiktok-ocr-video-evidence-pipeline-prd.md`

## What To Build

Analyze OCR and transcript evidence for unsafe health, medical, product, cure, symptom, or outcome claims. The output should separate what made a TikTok viral from what Nattome can safely reuse, soften, avoid, or reframe.

## Acceptance Criteria

- [ ] Claim Safety Review runs for every analyzed video.
- [ ] Cure claims are flagged.
- [ ] Guaranteed outcomes are flagged.
- [ ] One-night fix claims are flagged.
- [ ] Cancer prevention claims are flagged.
- [ ] Zero-side-effect claims are flagged.
- [ ] Detox or cleanse claims are flagged.
- [ ] Unverified doctor-recommended claims are flagged.
- [ ] Unsupported clinical percentages are flagged.
- [ ] Aggressive competitor claims are flagged.
- [ ] Each flagged claim includes reuse, soften, avoid, or reframe guidance for Nattome.

## Blocked By

- `0005-add-ocr-evidence-capture.md`
- `0006-add-multilingual-speech-transcription.md`
