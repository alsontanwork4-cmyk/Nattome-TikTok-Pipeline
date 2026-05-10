from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse
from urllib.request import urlopen


def source_video_filename(source: str) -> str:
    parsed = urlparse(source)
    suffix = Path(unquote(parsed.path)).suffix if parsed.scheme else Path(source).suffix
    return f"source_video{suffix or '.mp4'}"


def apify_authenticated_url(source: str) -> str:
    parsed = urlparse(source)
    if parsed.netloc != "api.apify.com":
        return source
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if query.get("token"):
        return source
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        return source
    query["token"] = token
    return urlunparse(parsed._replace(query=urlencode(query)))


def copy_or_download_video(source: str, destination: Path) -> dict[str, Any]:
    if not source:
        return {
            "status": "missing",
            "reason": "no downloadable video source was provided in candidate metadata",
        }

    parsed = urlparse(source)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if parsed.scheme in ("http", "https"):
            with urlopen(apify_authenticated_url(source), timeout=60) as response:
                destination.write_bytes(response.read())
        else:
            source_path = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(source)
            if not source_path.exists():
                return {
                    "status": "failed",
                    "reason": f"download source does not exist: {source}",
                    "source": source,
                }
            shutil.copyfile(source_path, destination)
    except Exception as exc:
        return {
            "status": "failed",
            "reason": str(exc),
            "source": source,
        }

    return {
        "status": "downloaded",
        "source": source,
        "artifact": destination.name,
        "bytes": destination.stat().st_size,
    }
