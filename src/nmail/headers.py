"""Headers extraction from Maildir files."""

from __future__ import annotations

from pathlib import Path


def extract_header(path: Path, header: str) -> str | None:
    """Extract a specific header value from a mail file."""
    text = path.read_text(errors="replace")
    lines = text.split("\n")
    lower = header.lower()
    for line in lines:
        if line.strip() == "":
            break  # end of headers
        if ":" in line:
            key, _, val = line.partition(":")
            if key.strip().lower() == lower:
                return val.strip()
    return None


def extract_body(path: Path) -> str:
    """Get everything after the first blank line (message body)."""
    text = path.read_text(errors="replace")
    parts = text.split("\n\n", 1)
    return parts[1].strip() if len(parts) > 1 else ""


def extract_headers_block(path: Path) -> str:
    """Get all headers (everything before first blank line)."""
    text = path.read_text(errors="replace")
    parts = text.split("\n\n", 1)
    return parts[0]
