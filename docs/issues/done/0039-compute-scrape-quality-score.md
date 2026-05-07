# Compute Scrape Quality Score

Labels: needs-triage
Type: AFK

## Parent

`docs/issues/0036-build-marketer-scrape-quality-dashboard.md`

## What to build

Add a scrape-only Scrape Quality Score for indexed runs. The score should help a Nattome marketer understand whether discovery produced useful TikToks, without mixing in downstream evidence extraction, claim safety, or manual review burden.

The score should be explainable through component drivers and should flag scores below 60 as needing attention without mutating scrape settings.

## Acceptance criteria

- [ ] Scrape Quality Score is computed on a 100-point scale.
- [ ] Score components cover candidate volume, eligibility yield, Nattome relevance, freshness, engagement strength, and duplicate/noise control.
- [ ] Claim safety, manual review burden, and evidence extraction success are excluded from the score.
- [ ] Score bands are `80-100` strong scrape, `60-79` usable scrape, and `<60` needs attention.
- [ ] Quality drivers explain what helped or hurt the score.
- [ ] Scores below 60 create an attention condition but do not change configuration or scheduled run behavior.
- [ ] Tests cover strong, usable, and needs-attention runs using representative indexed data.
- [ ] Tests prove downstream Pipeline Health failures do not reduce the Scrape Quality Score.

## Blocked by

- `docs/issues/0038-index-pipeline-artifacts-into-sqlite.md`
