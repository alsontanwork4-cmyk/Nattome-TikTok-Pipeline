# Browse And Curate Raw Scraped Videos

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Build the Scraped Content area around raw scraped videos as the primary content object. Marketers should be able to browse every indexed raw video, understand its scrape metadata, open the original TikTok URL, see whether it became eligible/selected/analyzed, and add lightweight labels and notes.

The MVP should not include embedded local video playback.

## Acceptance criteria

- [ ] Raw video browser lists indexed raw videos, including unselected videos.
- [ ] Each video shows author, caption, hashtags, source input where available, views, likes, comments, shares, created date, freshness, engagement, relevance, downloadability, run ID, config version, and status.
- [ ] Each video includes an outbound TikTok link.
- [ ] Video status distinguishes raw only, eligible, selected, and analyzed where data supports it.
- [ ] MVP does not embed or locally play source videos.
- [ ] Marketers can add and remove lightweight labels.
- [ ] Supported labels include Relevant, Irrelevant, Wrong Market, Great Hook, Good Nattome Fit, Competitor Inspiration, Save for Later, and Exclude Similar.
- [ ] Exclude Similar requires a short reason.
- [ ] Marketers can add and edit a short note.
- [ ] Labels and notes persist across runs by TikTok video ID.
- [ ] Tests cover label/note persistence and raw-video status display.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
