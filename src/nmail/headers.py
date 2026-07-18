"""Headers extraction from Maildir files."""

from __future__ import annotations

from pathlib import Path


def _folded_value(lines: list[str], start: int) -> str:
    """Collect a folded header value starting at `start`, handling RFC2822 continuation lines."""
    _, _, val = lines[start].partition(":")
    parts = [val.strip()]
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line == "":
            break
        if line[0] in (" ", "\t"):
            parts.append(line.strip())
        else:
            break
    return " ".join(parts)


def extract_header(path: Path, header: str) -> str | None:
    """Extract a specific header value from a mail file."""
    text = path.read_text(errors="replace")
    lines = text.split("\n")
    lower = header.lower()
    for i, line in enumerate(lines):
        if line == "":
            break  # end of headers
        # Skip continuation lines (folded header values)
        if line[0] in (" ", "\t"):
            continue
        if ":" in line:
            key, _, _ = line.partition(":")
            if key.strip().lower() == lower:
                return _folded_value(lines, i)
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
