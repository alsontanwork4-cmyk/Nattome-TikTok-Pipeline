from __future__ import annotations

NAV_ITEMS = (
    ("Overview", "/"),
    ("Report", "/report"),
    ("Run History", "/run-history"),
    ("Scrape Settings", "/scrape-settings"),
)

NAV_GROUPS = (
    ("Discovery", (
        ("Overview", "/", "overview"),
        ("Report", "/report", "report"),
        ("Run History", "/run-history", "history"),
    )),
    ("Quality", (
        ("Scrape Settings", "/scrape-settings", "settings"),
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
