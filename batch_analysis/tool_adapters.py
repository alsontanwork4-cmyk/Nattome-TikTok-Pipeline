from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import urlopen


def source_video_filename(source: str) -> str:
    parsed = urlparse(source)
    suffix = Path(unquote(parsed.path)).suffix if parsed.scheme else Path(source).suffix
    return f"source_video{suffix or '.mp4'}"


def copy_or_download_video(source: str, destination: Path) -> dict[str, Any]:
    if not source:
        return {
            "status": "missing",
            "reason": "no downloadable video source was provided in candidate metadata",
        }

    parsed = urlparse(source)
    try:
        if parsed.scheme in ("http", "https"):
            with urlopen(source, timeout=60) as response:
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


def extract_timeline_frame(
    ffmpeg_bin: str,
    source_video_path: Path,
    timestamp_seconds: int | float,
    frame_path: Path,
) -> dict[str, Any]:
    command = [
        ffmpeg_bin,
        "-y",
        "-ss",
        str(timestamp_seconds),
        "-i",
        str(source_video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(frame_path),
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=60)
    except FileNotFoundError:
        return {
            "status": "failed",
            "reason": f"FFmpeg executable not found: {ffmpeg_bin}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": f"FFmpeg timed out at {timestamp_seconds} seconds",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or "FFmpeg frame extraction failed",
        }

    return {"status": "completed"}


def ocr_command(engine: str, executable: str, frame_path: Path) -> list[str]:
    if engine == "paddleocr":
        return [executable, "--image_dir", str(frame_path), "--lang", "ch"]
    return [executable, str(frame_path), "stdout", "-l", "eng+msa+chi_sim+chi_tra"]


def run_ocr_command(executable: str, engine: str, frame_path: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ocr_command(engine, executable, frame_path),
            text=True,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError:
        return {
            "status": "tool_missing",
            "reason": f"{engine} executable not found: {executable}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": f"{engine} timed out for {frame_path.name}",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or f"{engine} OCR failed",
        }

    return {
        "status": "completed",
        "text": completed.stdout.strip(),
    }


def extract_audio(
    source_video_path: Path,
    audio_path: Path,
    ffmpeg_bin: str,
) -> dict[str, Any]:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(source_video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=60)
    except FileNotFoundError:
        return {
            "status": "failed",
            "reason": f"FFmpeg executable not found: {ffmpeg_bin}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": "FFmpeg timed out during audio extraction",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or "FFmpeg audio extraction failed",
        }

    return {
        "status": "extracted",
        "path": str(audio_path),
    }


def run_transcription_command(transcription_bin: str, audio_path: Path) -> dict[str, Any]:
    command = [
        transcription_bin,
        str(audio_path),
        "--language",
        "auto",
        "--task",
        "transcribe",
    ]
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=120)
    except FileNotFoundError:
        return {
            "status": "tool_missing",
            "reason": f"transcription executable not found: {transcription_bin}",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "reason": "transcription command timed out",
        }

    if completed.returncode != 0:
        return {
            "status": "failed",
            "reason": completed.stderr.strip() or "transcription command failed",
        }

    return {
        "status": "completed",
        "stdout": completed.stdout.strip(),
    }
