#!/usr/bin/env python3
"""
Post the daily Nattome brief to Telegram.

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from env. If either is missing,
exits silently with code 0 — the SKILL treats Telegram as optional.

Long briefs are split into multiple messages (Telegram cap is 4096 chars).
Falls back to sending as a document if a single section is still too long.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.telegram.org"
MAX_MESSAGE_LEN = 3800  # leave headroom under the 4096 hard cap


def chunk_markdown(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    """Split on headings first, then paragraphs, then lines, never mid-word."""
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current = ""
    # Prefer splitting on H2/H3 boundaries
    parts = text.split("\n## ")
    for i, part in enumerate(parts):
        prefix = "## " if i > 0 else ""
        block = prefix + part
        if len(current) + len(block) + 1 <= max_len:
            current = (current + "\n" + block) if current else block
        else:
            if current:
                chunks.append(current)
            if len(block) <= max_len:
                current = block
            else:
                # Hard split on lines
                lines = block.splitlines(keepends=True)
                buf = ""
                for line in lines:
                    if len(buf) + len(line) > max_len:
                        chunks.append(buf)
                        buf = line
                    else:
                        buf += line
                current = buf
    if current:
        chunks.append(current)
    return chunks


def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"{API_BASE}/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def send_document(token: str, chat_id: str, filepath: Path, caption: str = "") -> dict:
    """Multipart upload — used as a fallback when a single chunk is too big."""
    url = f"{API_BASE}/bot{token}/sendDocument"
    boundary = "----nattomeBoundary7c3f"
    content = filepath.read_bytes()
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode())
    if caption:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode())
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
        f"filename=\"{filepath.name}\"\r\nContent-Type: text/markdown\r\n\r\n".encode()
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser(description="Send the daily Nattome brief to Telegram")
    ap.add_argument("--brief", type=Path, required=True, help="Path to the markdown brief")
    ap.add_argument("--as-document", action="store_true",
                    help="Always send as a .md attachment instead of inline messages")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[info] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set; skipping Telegram delivery", file=sys.stderr)
        return 0

    if not args.brief.exists():
        print(f"error: brief not found at {args.brief}", file=sys.stderr)
        return 2

    text = args.brief.read_text(encoding="utf-8")

    if args.as_document:
        send_document(token, chat_id, args.brief, caption="Nattome daily TikTok brief")
        print("[ok] sent brief as document", file=sys.stderr)
        return 0

    chunks = chunk_markdown(text)
    # If any single chunk is still too big, give up on chunking and send as doc
    if any(len(c) > 4000 for c in chunks):
        send_document(token, chat_id, args.brief, caption="Nattome daily TikTok brief")
        print("[ok] sent brief as document (too long for inline)", file=sys.stderr)
        return 0

    for i, chunk in enumerate(chunks, 1):
        suffix = f"\n\n_({i}/{len(chunks)})_" if len(chunks) > 1 else ""
        try:
            send_message(token, chat_id, chunk + suffix)
        except Exception as e:
            print(f"[warn] inline send failed ({e}); falling back to document", file=sys.stderr)
            send_document(token, chat_id, args.brief, caption="Nattome daily TikTok brief")
            return 0
    print(f"[ok] sent brief in {len(chunks)} message(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
