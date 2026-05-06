# Virality Analysis Framework

This is the lens for breaking down WHY a TikTok worked. Don't just describe what happened in the video — explain the mechanism.

## The five things you analyze, in order

### 1. Hook (first 1–3 seconds)

This is the single most important factor on TikTok. If the hook fails, nothing else matters.

Common hook patterns in the digestive-health / wellness space:

| Pattern | Example | Why it works |
|---|---|---|
| **Symptom recognition** | "If your stomach feels like a balloon every night…" | Triggers the "yes, that's me" reflex; algorithm reads completion |
| **Counter-intuitive claim** | "Stop drinking lemon water in the morning, here's why" | Pattern interrupt; creates curiosity gap |
| **POV / scenario** | "POV: you ate the entire pizza" | Relatable, low-stakes, pulls in scrollers |
| **Visual shock** | A bloated belly time-lapse | Stops the scroll on visual alone |
| **Authority drop** | "I'm a gut health doctor and this is what I'd never eat" | Borrowed authority + curiosity |
| **Result tease** | "How I fixed my bloating in 30 days" | Promise of payoff if you watch |
| **Confession** | "I have IBS and here's what no one tells you" | Vulnerability triggers parasocial connection |

When you analyze, name the hook pattern by type. "It's a symptom-recognition hook with a visual proof shot at 0:02" is much more useful than "good hook".

### 2. Pacing

Count cuts in the first 10 seconds. Note the energy curve.

- **High pace (8+ cuts in 10s):** typical for listicle / tip videos. Works because it forces re-attention every 1–2s.
- **Slow pace (1–3 cuts in 10s):** typical for talking-head storytelling and POV videos. Works when the content itself holds attention.
- **Energy curve:** does it open hot and stay hot, or open hot, dip, then payoff at the end? Most viral health videos open with the hook, dip into context, then resolve with the takeaway around 70–80% of the way through.

If pacing feels off (e.g. video is 60s long with no cuts and no clear payoff), that often correlates with low engagement even at high views — flag it.

### 3. Structure

The macro-shape of the video. Common structures:

- **Listicle** — "3 things I do for…", "5 foods that…". Predictable but reliable.
- **Before/After** — visual or claim-based transformation. Strong on retention.
- **POV** — first-person scenario. Strong on relatability.
- **Tutorial / how-to** — practical, save-worthy. Lower top-end virality but strong saves.
- **Reaction / duet / stitch** — borrowed virality from another video.
- **Story arc** — setup → conflict → resolution. Hard to do in 30s but very strong when it works.
- **Mythbuster** — "you've been told X, but actually Y". Pattern-interrupt structure.
- **Day-in-the-life** — VLOG. Builds parasocial trust over time.

### 4. Emotional trigger

What did the viewer feel that made them complete, like, comment, or save? Be specific.

- **Recognition / validation** — "yes, that's me, I'm not alone"
- **Curiosity gap** — "I need to know what they say next"
- **Schadenfreude** — "haha that poor person" (lower-class trigger, use with care)
- **Aspiration** — "I want to live like that"
- **Fear / urgency** — "wait, am I doing this wrong?"
- **Relief / reassurance** — "ok, this is fixable"
- **Outrage** — "I can't believe they sell this" (high virality, often low quality, off-brand for Nattome)
- **Empathy** — "this person is being honest about something hard"

For the Nattome use case, the emotional triggers we want to lean into are: **recognition, relief, reassurance, aspiration**. Avoid building angles on outrage or fear — that's off-brand.

### 5. Why this won

In 1–2 honest sentences, your read on what specifically the algorithm rewarded. Be specific. Examples:

- "Strong symptom-recognition hook + 9-cut pacing in the first 10s drove completion past 80%, which is the threshold the algorithm rewards."
- "It's borrowed virality — this is a duet of a 4M-view original. The audio + tag did most of the work; the creator's edit added little."
- "Slow-paced VLOG that worked because the audio choice hit the trending list and the visual was unusually clean."

If a video has high views but low engagement (low like ratio, almost no comments), say so. That usually means a paid push or a misleading hook. Those aren't models to copy.

## Engagement-rate sanity check

When ranking videos, don't go by views alone. Compute engagement rate:

```
engagement_rate = (likes + comments * 5 + shares * 10) / views
```

(Comments and shares matter more than likes — they signal real reaction.)

A video with 500K views and 0.5% engagement is probably a paid push or a bait hook. A video with 80K views and 8% engagement is genuinely resonating and is a better model to copy.

## Format-spotting cheatsheet (for the IDEATE step)

When you've analyzed a viral video, ask: which Nattome format would translate this best?

| The viral video is… | Nattome format to use |
|---|---|
| Pure talking head with a strong claim | Talking head — match the structure, swap in Nattome's claim |
| VLOG / day-in-the-life | VLOG — Maintainer avatar living their morning routine |
| POV → reveal | Both — VLOG opens the POV, talking head delivers the reveal |
| Symptom recognition + product reveal | Both — VLOG sells the relatability, talking head sells the credibility |
| Educational mythbuster | Talking head — clinical backing has a natural place here |
| Before/after | VLOG — needs visual proof, not a face on camera |

## When NOT to copy a viral video

Some viral patterns aren't worth chasing for Nattome:

- **Outrage-bait** — viral but off-brand
- **Fearmongering health claims** — "this kills you in your sleep" — opens us up to ASA / regulator issues
- **Crude humor / toilet humor** — fine on TikTok, off-brand for a clinically-backed retail product
- **Pseudoscience ("toxins", "cleanse")** — cheap reach, expensive to credibility
- **Pure dance / sound trends with no health connection** — no organic angle, forced will read as cringe

If the top viral video falls into one of these, say so in the analysis and either reframe or skip the angle. Better to deliver 4 strong angles than 5 with one forced.
