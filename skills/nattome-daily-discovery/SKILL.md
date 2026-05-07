---
name: nattome-tiktok-discovery
description: Daily viral TikTok discovery and evidence-ready handoff pipeline for Nattome (Atomic Group's flagship digestive-health brand for Malaysians). Scrapes TikTok via Apify across hashtags, keywords, and competitor profiles, keeps candidates with downloadable source videos, ranks the top 5 viral videos, writes a daily brief, and creates the top-5 handoff for Gemini video evidence analysis. Use this skill for discovery, ranking, metadata-informed notes, and handoff creation. Do not present daily-discovery angles as production-ready unless the source video has been downloaded and analyzed through `nattome-batch-analysis` / Gemini 2.5 Flash. Use whenever the user mentions TikTok content discovery, viral content research, the daily content brief, content ideas for Nattome, gut-health TikTok trends, competitor TikTok analysis, Apify scraping, or asks "what's trending today", "give me content ideas", "run the daily brief", "find viral TikToks", "what should we post", or wants a breakdown of why a specific video went viral. Enforces Nattome's updated brand voice: natural fermented-soy gut care, relief plus repair, named clinical backing (UCSI / ClinicalTrials.gov NCT06524271), pharmacy trust signals (CARiNG / BIG / Watsons / Wellings), family-care messaging, sincere Malaysian tone, and strict no-cure/no-fearmongering claim guardrails.
---

# Nattome TikTok Daily Content Discovery

You are running Nattome's daily TikTok content discovery pipeline. Your job is to find evidence-ready viral candidates, preserve source videos where possible, and create a practical handoff for video evidence analysis. Do not turn metadata alone into confident production claims.

## What Nattome Is (Memorize This)

**Brand:** Nattome - Atomic Group's flagship digestive-health brand: a natural, clinically backed gut-care system for Malaysians who want relief now and repair over time.

**Products:**
- **DH** - daily digestive maintenance, daily care, and gut-lining support
- **DR** - faster relief for reflux, bloating, heartburn, indigestion, and gastric discomfort
- **DH-R / recovery** - deeper gut repair and recovery

**Public positioning:** fermented soy, Gastro-AD, natural stomach repair, and gut health as everyday self-care, not only emergency medicine.

**Channels (2026):** retail has surpassed online growth. Distribution includes CARiNG Pharmacy, BIG Pharmacy, Watsons, Wellings, and other pharmacies, with a target path toward 4,000 stores.

**Clinical backing:** UCSI and ClinicalTrials.gov NCT06524271. Use exact substantiated outcomes only. Say "clinically studied" or "shown in study," not vague "science-backed."

**Avatars (always pick one when generating an angle):**
- *The Sufferer* - has reflux, bloating, heartburn, indigestion, or gastric discomfort; wants relief quickly and may feel anxious or embarrassed
- *The Maintainer* - wants daily gut care, natural ingredients, family-safe routines, and long-term repair instead of repeat antacid use
- *The Pharmacy Browser* - sees Nattome in CARiNG, BIG, Watsons, Wellings, or through pharmacist recommendation; needs fast proof and simple product choice
- *The Family Caregiver* - buys for parents, spouse, children, or older relatives; responds to "care for their stomach" and Parents' Day style messaging
- *The Concerned Preventer* - sees stomach issues as a warning sign; responds to education, risk factors, clinical data, and "start before it gets worse"

**Voice keywords:**
- Natural, gentle, clinically backed, daily, repair, relief, gut lining, stomach protection, family care, pharmacy trusted, fermented soy, Gastro-AD
- Natural vs chemical: position against antacid-only habits and Gaviscon-style temporary relief without aggressive competitor attacks unless legally approved
- Relief plus repair: DR for immediate discomfort; DH for daily care and gut-lining support; DH-R/recovery for deeper gut repair
- Sincere, practical, Malaysian, warm. Never "miracle cure" energy.

**Tone rules:** Warm but not childish. Educational but not academic. Direct but not fearmongering. Use symptom-led openings like "Always bloated after meals?", "Heartburn again?", or "Relying on antacids too often?", then move quickly to the natural mechanism, clinical proof, product choice, and pharmacy or WhatsApp CTA.

**Claim guardrails:** Do not promise cures, cancer prevention, zero side effects, or guaranteed medical outcomes. Do not overuse scare tactics like "stomach cancer is waiting for you." Do not make Nattome feel like a short-term painkiller.

Read `references/nattome_brand.md` for the full voice/style guide and the do/don't list before generating any angle copy.

## The Pipeline (High-Level)

```text
1. DISCOVER   -> scripts/scrape_tiktok.py runs hashtag + keyword + competitor scrapes
2. FILTER     -> prefer candidates with `video_download_url`; download source videos with `--download-videos`
3. RANK       -> score by virality (views, engagement rate, recency)
4. PREVIEW    -> write metadata-informed notes only; label unknown video-content details clearly
5. HANDOFF    -> write daily_brief_YYYY-MM-DD.md and top-5 JSON for Gemini evidence analysis
6. ANALYZE    -> for real shootable angles, run `nattome-batch-analysis --mode daily` on the handoff
```

The whole run should take 3-8 minutes depending on Apify response time.

## Step-By-Step Workflow

### Step 1 - Confirm Scope And Run Discovery

Default daily run: hashtags + keywords + competitor profiles, top 5. If the user says something narrower (for example, "just analyze this one URL" or "do bloating only"), respect that and skip what's not asked for.

Check that `APIFY_TOKEN` is set in the environment. If it's not, stop and ask the user to provide it. Do not fake the run.

Run the discovery:

```powershell
python skills/nattome-daily-discovery/scripts/scrape_tiktok.py `
  --output data/raw_scrapes/nattome_raw_$(Get-Date -Format yyyyMMdd)_top30.json `
  --top 30 `
  --download-videos `
  --daily-selection-output data/daily_selections/nattome_daily_$(Get-Date -Format yyyyMMdd)_top5.json
```

(POSIX equivalent: `python skills/nattome-daily-discovery/scripts/scrape_tiktok.py --output data/raw_scrapes/nattome_raw_$(date +%Y%m%d)_top30.json --top 30 --download-videos --daily-selection-output data/daily_selections/nattome_daily_$(date +%Y%m%d)_top5.json`)

The script writes the full ranked scrape and a separate daily evidence-analysis handoff. The handoff contains the same top videos used for the daily brief and is the source for daily video evidence analysis. Treat candidates without `video_download_url` as metadata-only previews, not evidence-ready production inputs. If `--top` is omitted, the scraper returns only the top 5, but the normal daily pipeline should keep the top-30 scrape for audit and the top-5 handoff for analysis.

On Windows, keep all scraper JSON/config/brief files in UTF-8. The bundled scripts explicitly read config and markdown as UTF-8 and write JSON as UTF-8 with `ensure_ascii=False`, so TikTok captions with Unicode characters do not fail under the default `cp1252` console/file encoding.

If Apify returns errors or empty results, report it honestly to the user and ask whether to retry, change inputs, or proceed with whatever did come back. Do not fabricate viral videos.

### Step 2 - Preview Each Top Candidate

For each of the top 5 candidates, do a structured preview. Read `references/virality_framework.md` first. It explains the lens you're using.

If Gemini video evidence has not been generated yet, do not claim to know exact video content. The preview may cover:

- **Topic** - what it is actually about, in plain English
- **Metadata signals** - caption, hashtags, author, engagement, recency, and URL
- **Likely hook direction** - inferred from metadata only, clearly labeled as an inference
- **Likely structure** - inferred from caption/topic only, clearly labeled as an inference
- **Emotional trigger** - likely relatability, validation, fear, curiosity, etc., based on available metadata
- **Why this may have won** - your honest 1-2 sentence read based on metadata and engagement signals

If a video's view count is high but engagement rate is poor, say so. That is a different signal, such as paid push or a bait-y hook that did not deliver. Do not pretend every viral video is a model.

### Step 3 - Generate Preliminary Angles Only When Evidence Is Missing

If Gemini video evidence is missing, any angles are **preliminary metadata-informed ideas**, not evidence-backed shootable angles. Label them as preliminary and recommend running `nattome-batch-analysis --mode daily` before production decisions.

For each viral topic, preliminary angles may include:

| Field | What goes here |
|---|---|
| Angle title | Short, scrollable, in plain language |
| Hook direction | Draft opening line for Nattome, not the original video's verified first 3 seconds |
| Avatar | Sufferer / Maintainer / Pharmacy Browser / Family Caregiver / Concerned Preventer |
| Format | **Talking head** / **VLOG** / **Both** (Nattome currently uses all three - pick what fits the angle) |
| Product tie-in | DH / DR / DH-R or recovery - and *why* this product fits the moment |
| Script outline | 4-6 beats, not a full script. Include where the clinical backing lands if it lands. |
| Evidence status | `metadata_only`, `video_downloaded`, or `gemini_evidence_completed` |
| Why this may work for Nattome | One line connecting the likely emotional trigger to Nattome's positioning |

Only call an angle **shootable** when source-video evidence exists and supports the hook, structure, pacing, and emotional-trigger read. For production-ready outputs, run `nattome-batch-analysis`, which uses Gemini 2.5 Flash and writes evidence-backed Shootable Angles.

**Format selection rules** (use judgment, these are guides not laws):
- **Talking head** - when the angle hinges on authority, education, or a clear claim. Good for clinical-backing references and product explainers.
- **VLOG** - when the angle hinges on relatability, daily-life moments, or "show don't tell" symptom storytelling. Good for the Maintainer, Pharmacy Browser, and Family Caregiver avatars.
- **Both** - when the angle has a setup-payoff structure: VLOG opens with the relatable problem, talking head delivers the answer. This is often Nattome's strongest pattern because it combines emotional recognition with credibility.

**Voice guardrails** (non-negotiable; see brand reference for details):
- Never say "miracle", "cure", "instant fix" without context, or anything that sounds like generic supplement advertising.
- When you reference clinical backing, name it: "UCSI" or "ClinicalTrials.gov NCT06524271". Vague "science-backed" or "studies show" is off-brand unless paired with a specific citation.
- If you're positioning against Gaviscon or antacid-only habits, frame it as natural vs chemical / relief plus repair / daily care vs temporary relief. Do not trash competitors by name in scripted copy.
- Use pharmacy trust signals where relevant: CARiNG, BIG, Watsons, Wellings, pharmacist recommendation, or "not just another online health ad."
- Family-care angles should sound warm and practical: "care for your parents' stomach," "daily gut care for the people you love," "health is the best gift."
- Do not promise cures, cancer prevention, zero side effects, or guaranteed medical outcomes.
- Do not overuse scare tactics like "stomach cancer is waiting for you."
- If the trend itself does not fit Nattome's voice, for example crude, mocking, or fearmongering, say so and either reframe sincerely or recommend skipping it.

### Step 4 - Write The Daily Discovery Handoff

Use the template at `skills/nattome-daily-discovery/assets/daily_brief_template.md`. Save to:

```text
outputs/daily_briefs/daily_brief_YYYY-MM-DD.md
```

The brief is a discovery and evidence-analysis handoff, not the current final production report. Make it scannable so the marketing team can quickly decide what to send into Gemini analysis next. Use tables for preliminary angle grids only when helpful, short paragraphs for metadata preview, and links to original TikToks.

For final production-ready outputs and evidence-backed shootable angles, use `nattome-batch-analysis`, which analyzes the downloaded videos with Gemini 2.5 Flash and writes the Top 5 Creative Production Report and Excel planning workbook under `outputs/reports/YYYY-MM-DD/`.

### Step 5 - Optional Telegram Delivery

If `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are both set in the environment, also push the brief:

```powershell
python skills/nattome-daily-discovery/scripts/telegram_send.py `
  --brief outputs/daily_briefs/daily_brief_YYYY-MM-DD.md
```

If either env var is missing, skip silently and just confirm the markdown file path. Do not pester the user about Telegram setup unless they ask.

## When The User Gives You A Single URL Instead Of A Daily Run

Skip discovery. If the user needs production-ready angles, run the video through `nattome-batch-analysis`/Gemini evidence analysis before generating shootable angles. If only metadata or a URL is available, output a single-video preview with preliminary ideas and clearly label missing evidence. The full daily template is not needed.

## When The User Is Clearly Ideating, Not Running The Daily

If the user says "give me ideas about [topic]" without asking for the scrape, you can generate topic-based brainstorms using the brand voice, but label them as brainstorms. Ask whether they want discovery plus Gemini video evidence analysis if they need production-ready angles.

## Reference Files

- **`references/nattome_brand.md`** - full brand voice, tone rules, do/don't list, product positioning details. Read before writing any angle copy.
- **`references/virality_framework.md`** - the analysis lens: hook taxonomy, pacing patterns, structure types, emotional triggers, common TikTok formats in the health/wellness space.

## Bundled Scripts

- **`scripts/scrape_tiktok.py`** - Apify TikTok scraper. Runs hashtag + keyword + profile scrapes, ranks results, writes JSON.
- **`scripts/telegram_send.py`** - posts the markdown brief to a Telegram chat via bot API.

## Bundled Assets

- **`assets/daily_brief_template.md`** - the output format. Copy this and fill in.
- **`assets/config.example.json`** - example config (hashtags, keywords, competitor handles). Copy to `config.json` and edit, or pass `--config` to the scraper.
