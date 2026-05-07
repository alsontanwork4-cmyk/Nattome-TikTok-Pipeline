from __future__ import annotations

NAV_ITEMS = (
    ("Overview", "/"),
    ("Run History", "/run-history"),
    ("Scrape Settings", "/scrape-settings"),
    ("Recommendations", "/recommendations"),
    ("Pattern Library", "/pattern-library"),
    ("Nattome POV Library", "/nattome-pov-library"),
    ("Pipeline Architecture", "/pipeline-architecture"),
)

NAV_GROUPS = (
    ("Discovery", (
        ("Overview", "/", "overview"),
        ("Run History", "/run-history", "history"),
    )),
    ("Quality", (
        ("Scrape Settings", "/scrape-settings", "settings"),
        ("Recommendations", "/recommendations", "recommendations"),
    )),
    ("Library", (
        ("Pattern Library", "/pattern-library", "pattern"),
        ("Nattome POV Library", "/nattome-pov-library", "pov"),
    )),
    ("System", (
        ("Pipeline Architecture", "/pipeline-architecture", "architecture"),
    )),
)

CURATION_LABELS = (
    "Relevant",
    "Irrelevant",
    "Wrong Market",
    "Great Hook",
    "Good Nattome Fit",
    "Competitor Inspiration",
    "Save for Later",
    "Exclude Similar",
)
