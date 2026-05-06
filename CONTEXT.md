# Nattome TikTok Video Analysis

This context defines the language for turning TikTok discovery results into evidence-backed creative reports for Nattome.

## Language

**Video Evidence Report**:
A timestamped analysis document for one TikTok video that combines metadata, OCR, transcript, visual observations, pacing, and Nattome creative recommendations.
_Avoid_: OCR report, video summary, trend report

**Hybrid Timeline**:
A timestamped analysis timeline that samples every second, but adds extra frames when the video changes visually or new text appears.
_Avoid_: strict one-frame-per-second timeline, full-frame dump

**Evidence Bundle**:
The collected source materials used to produce one **Video Evidence Report**, including metadata, video file, OCR timeline, transcript, audio/music trend analysis, and optional subtitles or cover images.
_Avoid_: scrape result, OCR files

**Audio/Music Trend Analysis**:
An assessment of the video's sound, music, voiceover, and audio format as creative evidence for why the TikTok may be engaging.
_Avoid_: audio metadata only

**Baseline Audio Analysis**:
The required audio review for every video, covering sound title, original/reused status, voiceover format, mood, hook support, and whether Nattome should copy, avoid, or adapt the audio style.
_Avoid_: music title only

**Deep Sound Research**:
An optional deeper check into whether a sound is trending across TikTok, what format it belongs to, how many videos use it, and whether it is brand-safe for Nattome.
_Avoid_: mandatory sound scrape

**Report Form**:
The fixed section structure used by every **Video Evidence Report**, covering video reference, executive creative read, hook audit, hybrid timeline, OCR summary, transcript summary, audio/music analysis, virality breakdown, Nattome POV, shootable angles, and evidence quality.
_Avoid_: loose notes, ad hoc report

**Batch Analysis Run**:
A processing run that takes a selected set of TikTok videos and produces one **Video Evidence Report** per video, plus a cross-video pattern summary.
_Avoid_: one-off video audit as the default

**Cross-Video Pattern Summary**:
A batch-level report that compares analyzed videos to identify repeatable hooks, formats, emotional triggers, audio patterns, risky claims, and priority Nattome shoot opportunities.
_Avoid_: folder of disconnected reports

**Default Batch**:
The standard **Batch Analysis Run** size of 10 TikTok videos for pattern discovery.
_Avoid_: unlimited batch, all scraped videos

**Viral Relevance Selection**:
The rule for choosing videos for a **Batch Analysis Run** by ranking candidates on virality, recency, and relevance to Nattome, without forcing category quotas.
_Avoid_: fixed topic quotas, top views only

**Minimum Eligibility Filter**:
The baseline filter applied before selection to remove videos that are too small, too old, weakly engaged, irrelevant, or unsafe for Nattome analysis.
_Avoid_: selecting every scraped result

**Minimum Filter Thresholds**:
The default eligibility thresholds for batch selection: at least 10,000 views, no older than 30 days, at least 3% weighted engagement rate, a usable TikTok link, a downloadable video, and relevance to Nattome.
_Avoid_: no-threshold selection

**Evidence Quality Score**:
A confidence rating for one **Video Evidence Report** based on OCR quality, transcript quality, video download quality, subtitle availability, timeline completeness, and manual review needs.
_Avoid_: hidden confidence, unqualified analysis

**Batch Output Set**:
The required deliverables from one **Batch Analysis Run**: markdown reports, structured JSON, and a spreadsheet summary.
_Avoid_: markdown-only output

**Run Folder**:
The timestamped folder containing one **Batch Output Set** and all per-video **Evidence Bundles** for a **Batch Analysis Run**.
_Avoid_: loose output files, shared evidence folder

**Multilingual Evidence Capture**:
OCR and transcription support for English, Malay, Mandarin Chinese, Simplified Chinese, Traditional Chinese, and Manglish or code-mixed English-Malay-Chinese TikTok content.
_Avoid_: English-only OCR, English-only transcript

**Manual Review Flag**:
A marker on a **Video Evidence Report** showing that a human should inspect the video because OCR, transcript, hook detection, language detection, audio analysis, or claim interpretation may be unreliable.
_Avoid_: silent uncertainty

**Claim Safety Review**:
A review of any health, medical, product, cure, symptom, or outcome claims found in the TikTok, with guidance on whether Nattome can reuse, soften, avoid, or reframe the claim.
_Avoid_: copying viral claims directly

**Shootable Angle**:
A Nattome adaptation of a TikTok pattern with a hook, avatar, format, product tie-in, script beats, CTA, and claim guardrails, but not a full production script.
_Avoid_: full script by default, generic content idea

**Nattome Priority Score**:
A batch-level score that ranks TikTok patterns and **Shootable Angles** by viral strength, Nattome relevance, evidence confidence, brand safety, ease of production, and product fit.
_Avoid_: views-only priority, gut-feel ranking

**Evidence Artifact**:
A downloaded or generated source file used to support analysis, such as video, frame image, subtitle file, OCR output, transcript, or audio analysis.
_Avoid_: marketing asset, final creative asset

**Implementation Phase**:
A staged delivery slice for building the batch evidence pipeline without trying to implement downloading, OCR, transcription, reporting, and refinement all at once.
_Avoid_: big-bang implementation

**Evidence-First Analysis**:
Creative analysis generated from downloaded video evidence, OCR, transcript, audio analysis, and metadata rather than metadata alone.
_Avoid_: metadata-only inference, pretending to watch the video

**Tool Stack**:
The replaceable technical tool set used by the pipeline: Apify for TikTok discovery/download, FFmpeg for video processing, PaddleOCR as primary OCR, Tesseract as fallback OCR, Whisper-style multilingual transcription, markdown/JSON/XLSX outputs, and LLM-assisted analysis over the **Evidence Bundle**.
_Avoid_: hard-wired vendor lock-in

**Scheduled Analysis Run**:
A recurring **Batch Analysis Run** triggered by an automation runner such as Codex or Claude Code.
_Avoid_: manual-only workflow

**Telegram Delivery**:
The automated sending of batch results to a Telegram bot or chat after a **Batch Analysis Run** completes.
_Avoid_: local-only report delivery

**Weekly Evidence Brief**:
A scheduled weekly **Cross-Video Pattern Summary** delivered through markdown, JSON, spreadsheet, and Telegram notification.
_Avoid_: daily-only brief, metadata-only weekly summary

**Markdown Report Output**:
The required human-readable markdown output for each **Video Evidence Report** and the **Cross-Video Pattern Summary**.
_Avoid_: plain text dump

**Spreadsheet Summary Output**:
The required batch-level spreadsheet that gives the marketing team one scannable row per analyzed video with creative, evidence, and priority fields.
_Avoid_: JSON-only output

**Structured JSON Output**:
The required machine-readable output that preserves batch summaries, per-video evidence, timelines, OCR, transcripts, scoring, and creative recommendations for automation and future reuse.
_Avoid_: optional internal dump

## Relationships

- A **Video Evidence Report** belongs to exactly one TikTok video.
- A **Video Evidence Report** uses metadata, OCR, transcript, visual observations, and pacing evidence.
- A **Video Evidence Report** contains one **Hybrid Timeline**.
- A **Hybrid Timeline** contains regular one-second samples plus extra samples around hook moments, scene changes, and text changes.
- A **Video Evidence Report** is produced from one **Evidence Bundle**.
- An **Evidence Bundle** must include TikTok metadata, the video file, OCR timeline, speech transcript, audio/music trend analysis, and human-readable creative analysis inputs.
- An **Audio/Music Trend Analysis** belongs to exactly one **Evidence Bundle**.
- An **Audio/Music Trend Analysis** always includes **Baseline Audio Analysis**.
- An **Audio/Music Trend Analysis** includes **Deep Sound Research** only when the sound itself appears to be part of the video's viral mechanism.
- Every **Video Evidence Report** follows the same **Report Form**.
- A **Report Form** separates evidence sections from creative recommendation sections.
- A **Batch Analysis Run** produces one or more **Video Evidence Reports**.
- A **Batch Analysis Run** produces exactly one **Cross-Video Pattern Summary**.
- A **Cross-Video Pattern Summary** compares evidence from multiple **Video Evidence Reports**.
- A **Default Batch** contains 10 selected TikTok videos.
- A **Batch Analysis Run** may run as one video for debugging, 5 videos for quick mode, 10 videos as the default, or 20 videos for deep weekly research.
- A **Default Batch** is chosen with **Viral Relevance Selection**.
- A **Minimum Eligibility Filter** is applied before **Viral Relevance Selection**.
- A **Minimum Eligibility Filter** excludes videos under the chosen view threshold, older than the chosen recency threshold, weakly relevant to Nattome, or clearly unsafe because of crude humor, fearmongering, medical overclaims, or pseudoscience.
- The default **Minimum Filter Thresholds** are 10,000 views, 30-day maximum age, and 3% weighted engagement rate.
- The **Minimum Eligibility Filter** requires an original TikTok link and a usable video download.
- Every **Video Evidence Report** includes one **Evidence Quality Score**.
- An **Evidence Quality Score** is rated high, medium, or low confidence with a short reason.
- A **Batch Analysis Run** produces one **Batch Output Set**.
- A **Batch Output Set** must include human-readable markdown, machine-readable JSON, and a spreadsheet summary.
- A **Batch Analysis Run** is stored in exactly one **Run Folder**.
- A **Run Folder** contains batch-level markdown, JSON, and spreadsheet outputs plus one subfolder per analyzed video.
- Each per-video folder inside a **Run Folder** contains that video's **Evidence Bundle** and **Video Evidence Report**.
- Every **Evidence Bundle** requires **Multilingual Evidence Capture**.
- **Multilingual Evidence Capture** includes English, Malay, Mandarin Chinese, Simplified Chinese, Traditional Chinese, and Manglish or code-mixed English-Malay-Chinese.
- A **Video Evidence Report** includes a **Manual Review Flag** when the **Evidence Quality Score** is medium or low confidence.
- A **Manual Review Flag** is required when the first 3 seconds are unclear, OCR fails on visible text, transcript language detection fails, medical claims are detected, or the Nattome angle depends on an unverified claim.
- Every **Video Evidence Report** includes one **Claim Safety Review**.
- A **Claim Safety Review** flags cure claims, guaranteed outcomes, one-night fixes, cancer prevention claims, zero-side-effect claims, detox or cleanse claims, unverified doctor-recommended claims, unsupported clinical percentages, and aggressive competitor claims.
- A **Claim Safety Review** separates what made a TikTok viral from what Nattome can safely reuse.
- Every **Video Evidence Report** includes **Shootable Angles** as the default creative output.
- A **Shootable Angle** is not a full final script.
- The **Cross-Video Pattern Summary** identifies priority **Shootable Angles** that can later be expanded into full scripts.
- The **Cross-Video Pattern Summary** ranks patterns and **Shootable Angles** with a **Nattome Priority Score**.
- A **Nattome Priority Score** has six dimensions: viral strength, Nattome relevance, evidence confidence, brand safety, ease of production, and product fit.
- A **Nattome Priority Score** is scored out of 30 points.
- An **Evidence Bundle** contains **Evidence Artifacts**.
- Downloaded TikTok videos and extracted frames are **Evidence Artifacts**, not final marketing assets.
- **Evidence Artifacts** may be cleaned up after reports are approved, but JSON outputs, markdown reports, and spreadsheet summaries are durable records.
- The OCR analysis system is built through four **Implementation Phases**: Download + Run Folder, Evidence Extraction, Report Generation, and Refinement.
- Phase 1 creates the **Run Folder**, selects the **Default Batch**, downloads videos, stores metadata, and outputs a basic batch index.
- Phase 2 extracts **Hybrid Timeline** frames, runs OCR, transcribes audio, captures **Baseline Audio Analysis**, and stores evidence as JSON.
- Phase 3 generates **Video Evidence Reports**, the **Cross-Video Pattern Summary**, spreadsheet summary, **Evidence Quality Scores**, **Manual Review Flags**, and **Claim Safety Reviews**.
- Phase 4 adds **Deep Sound Research**, multilingual improvements, evidence cleanup, and full-script generation for selected **Shootable Angles**.
- The pipeline uses **Evidence-First Analysis** for all creative recommendations.
- **Evidence-First Analysis** depends on an **Evidence Bundle**, not metadata alone.
- The default **Tool Stack** uses Apify, FFmpeg, PaddleOCR, Tesseract fallback, Whisper-style multilingual transcription, markdown, JSON, XLSX, and LLM-assisted analysis.
- A **Scheduled Analysis Run** runs a **Batch Analysis Run** on a recurring schedule.
- A **Weekly Evidence Brief** is produced by a weekly **Scheduled Analysis Run**.
- **Telegram Delivery** sends the **Weekly Evidence Brief** summary, report links, and priority **Shootable Angles** after the run completes.
- Codex or Claude Code may act as the automation runner, but the domain output remains the same **Batch Output Set**.
- Every **Batch Analysis Run** produces **Markdown Report Output**.
- Every **Batch Analysis Run** produces one **Spreadsheet Summary Output**.
- Every **Batch Analysis Run** produces **Structured JSON Output**.
- **Structured JSON Output** is required even though markdown and spreadsheet outputs are the primary human-facing outputs.

## Example Dialogue

> **Dev:** "Should we generate an OCR report for each TikTok?"
> **Domain expert:** "Call it a **Video Evidence Report** because OCR is only one evidence source. The report also needs transcript, visual notes, pacing, and Nattome angles."
>
> **Dev:** "Should we OCR one frame per second?"
> **Domain expert:** "Use a **Hybrid Timeline**: sample every second, but capture extra frames when text or scenes change, especially inside the first 3 seconds."
>
> **Dev:** "Can subtitles be the evidence bundle?"
> **Domain expert:** "No. The **Evidence Bundle** must include metadata, the downloaded video, OCR, speech transcript, and **Audio/Music Trend Analysis** because TikTok performance can depend on sound as much as visuals."
>
> **Dev:** "Do we need to research every TikTok sound deeply?"
> **Domain expert:** "No. Every video gets **Baseline Audio Analysis**. Use **Deep Sound Research** only when the sound itself seems to drive the trend."
>
> **Dev:** "Can each report use whatever headings make sense?"
> **Domain expert:** "No. Use one **Report Form** so every TikTok can be compared consistently and the marketing team can scan evidence before recommendations."
>
> **Dev:** "Should we analyze videos one at a time?"
> **Domain expert:** "Default to a **Batch Analysis Run** because the goal is finding repeatable patterns across many videos, not only understanding one TikTok."
>
> **Dev:** "How many videos should a normal batch include?"
> **Domain expert:** "Use a **Default Batch** of 10 videos. Use 5 for a quick pilot, 1 for debugging, and 20 only for deeper weekly research."
>
> **Dev:** "Should the default batch force a mix like 3 education videos and 2 POV videos?"
> **Domain expert:** "No. Use **Viral Relevance Selection**: rank by virality, recency, and Nattome relevance after applying a **Minimum Eligibility Filter**."
>
> **Dev:** "What makes a TikTok eligible for the default batch?"
> **Domain expert:** "Apply the **Minimum Filter Thresholds** first: 10,000+ views, 30 days old or newer, 3%+ weighted engagement, usable link, downloadable video, and Nattome relevance."
>
> **Dev:** "Can we trust every OCR report equally?"
> **Domain expert:** "No. Every **Video Evidence Report** needs an **Evidence Quality Score** so the team knows whether OCR, transcript, and timeline evidence are reliable enough for creative decisions."
>
> **Dev:** "Is markdown enough as the output?"
> **Domain expert:** "No. A **Batch Output Set** must include markdown reports, structured JSON, and a spreadsheet summary so both humans and automation can use the analysis."
>
> **Dev:** "Where should all the OCR outputs go?"
> **Domain expert:** "Use one **Run Folder** per batch run, with batch-level outputs at the top and one evidence/report folder per video."
>
> **Dev:** "Can the OCR and transcript assume English only?"
> **Domain expert:** "No. Use **Multilingual Evidence Capture** because Nattome's Malaysian TikTok content may use English, Malay, Mandarin Chinese, Simplified Chinese, Traditional Chinese, and Manglish or code-mixed speech."
>
> **Dev:** "Should the system ask for manual review?"
> **Domain expert:** "Yes. Add a **Manual Review Flag** when evidence quality is medium or low, or when the creative recommendation depends on uncertain OCR, transcript, language, audio, or medical-claim evidence."
>
> **Dev:** "Can Nattome reuse a viral health claim if it performed well?"
> **Domain expert:** "No. Every **Video Evidence Report** needs a **Claim Safety Review** to decide whether the claim should be reused, softened, avoided, or reframed for Nattome."
>
> **Dev:** "Should the batch report produce full scripts for every angle?"
> **Domain expert:** "No. Default to **Shootable Angles** so the team gets hooks, formats, product tie-ins, beats, CTAs, and guardrails without bloating the report."
>
> **Dev:** "How do we decide what Nattome should shoot first?"
> **Domain expert:** "Use a **Nattome Priority Score** so viral strength is balanced against Nattome relevance, evidence confidence, brand safety, ease of production, and product fit."
>
> **Dev:** "Are downloaded TikTok videos marketing assets?"
> **Domain expert:** "No. Treat them as **Evidence Artifacts** for audit and analysis. They may be deleted later, while reports and structured outputs remain."
>
> **Dev:** "Should we build everything in one pass?"
> **Domain expert:** "No. Use four **Implementation Phases** so the team can validate downloading and evidence capture before investing in reporting, sound research, and full-script generation."
>
> **Dev:** "Can the LLM infer the video structure from captions and stats?"
> **Domain expert:** "No. Use **Evidence-First Analysis**: the LLM should analyze downloaded video evidence, OCR, transcript, audio analysis, and metadata."
>
> **Dev:** "Should the team manually run this every week?"
> **Domain expert:** "No. Use a **Scheduled Analysis Run** and **Telegram Delivery** so the **Weekly Evidence Brief** reaches the team automatically."
>
> **Dev:** "What should the team receive after a batch run?"
> **Domain expert:** "They need **Markdown Report Output** for detailed reading, **Spreadsheet Summary Output** for fast comparison, and **Structured JSON Output** for automation and future reuse."

## Flagged Ambiguities

- "OCR report" was too narrow because the desired report includes more than on-screen text; resolved as **Video Evidence Report**.
- "Every second" was clarified to mean a baseline one-second sampling rate, not ignoring fast cuts or text changes; resolved as **Hybrid Timeline**.
- "Evidence" was clarified to include audio/music trend analysis as mandatory, not optional.
- "Audio analysis" was split into **Baseline Audio Analysis** for every report and **Deep Sound Research** only when the sound is a likely viral driver.
- "Report" was clarified as a fixed **Report Form**, not ad hoc notes, with evidence first and Nattome recommendations after.
- "Video analysis" was clarified as batch-first because the business goal is pattern discovery across many videos.
- Batch size was resolved as 10 videos by default, with 1, 5, and 20-video modes for debug, quick, and deep research use cases.
- Selection was resolved as **Viral Relevance Selection**, not fixed content quotas.
- "Anatomy relevance" was interpreted as Nattome relevance.
- Minimum filters are part of selection and should run before ranking.
- Minimum filter thresholds were resolved as 10,000 views, 30-day maximum age, 3% weighted engagement, original TikTok link, downloadable video, and Nattome relevance.
- Evidence confidence was resolved as a required **Evidence Quality Score** on every **Video Evidence Report**.
- Batch output was resolved as markdown, JSON, and spreadsheet summary, all required.
- Batch storage was resolved as one **Run Folder** per **Batch Analysis Run**.
- Language support was resolved as required **Multilingual Evidence Capture** for English, Malay, Mandarin Chinese, Simplified Chinese, Traditional Chinese, and Manglish/code-mixed English-Malay-Chinese.
- Manual review was resolved as automation-first with a required **Manual Review Flag** for medium/low confidence evidence or uncertain claim interpretation.
- Health and product claim handling was resolved as a required **Claim Safety Review** on every **Video Evidence Report**.
- Creative output was resolved as **Shootable Angles** by default, with full scripts deferred to selected winners.
- Batch prioritization was resolved as a **Nattome Priority Score** with six dimensions and a 30-point total.
- Downloaded videos, frames, subtitles, OCR, transcripts, and audio outputs were resolved as **Evidence Artifacts**, with optional cleanup after report approval.
- Implementation was resolved as four phases: Download + Run Folder, Evidence Extraction, Report Generation, and Refinement.
- Tooling was resolved as Apify, FFmpeg, PaddleOCR, Tesseract fallback, Whisper-style multilingual transcription, markdown, JSON, XLSX, and LLM-assisted **Evidence-First Analysis**.
- Recurring delivery was added as a **Scheduled Analysis Run** with **Telegram Delivery** for a **Weekly Evidence Brief**.
- Output was resolved as required markdown reports, required structured JSON, and a required spreadsheet summary.
