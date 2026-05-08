from __future__ import annotations

import os
from pathlib import Path


def parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].lstrip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def candidate_dotenv_paths(start_paths: list[Path]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for start in start_paths:
        current = start.resolve()
        if current.is_file():
            current = current.parent
        for directory in (current, *current.parents):
            dotenv = directory / ".env"
            if dotenv not in seen:
                seen.add(dotenv)
                paths.append(dotenv)
    return paths


def load_dotenv_files(
    start_paths: list[Path] | None = None,
    *,
    override: bool = False,
) -> dict[str, str]:
    """Load nearest .env files into os.environ without replacing exported values."""
    if os.environ.get("NATTOME_DISABLE_DOTENV"):
        return {}
    starts = start_paths or [Path.cwd()]
    loaded: dict[str, str] = {}
    for dotenv in candidate_dotenv_paths(starts):
        if not dotenv.exists():
            continue
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            parsed = parse_dotenv_line(line)
            if parsed is None:
                continue
            key, value = parsed
            if override or not os.environ.get(key):
                os.environ[key] = value
                loaded[key] = str(dotenv)
    return loaded
