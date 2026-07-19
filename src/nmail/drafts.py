"""Draft helpers: create, validate, queue."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .config import get_config
from .headers import extract_header
from .maildir import ensure_maildir


def create_draft(
    template: str = "default",
    to: str | None = None,
    subject: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
    profile: str | None = None,
) -> Path:
    """Create a new draft file from a template. Returns path to draft."""
    cfg = get_config()
    prof = profile if profile is not None else cfg.profile or ""
    ensure_maildir(prof)
    drafts_dir = cfg.profile_path(prof, "drafts")
    drafts_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    draft_path = drafts_dir / f"{ts}.md"

    template_file = cfg.templates_dir / f"{template}.md"
    if template_file.exists():
        content = template_file.read_text()
    else:
        content = "From: \nTo: \nCc: \nSubject:\n\n"

    if to:
        content = _set_header(content, "To", to)
    if subject:
        content = _set_header(content, "Subject", subject)
    if cc:
        content = _set_header(content, "Cc", cc)
    if bcc:
        content = _set_header(content, "Bcc", bcc)

    _atomic_write(draft_path, content)
    return draft_path


def _set_header(content: str, header: str, value: str) -> str:
    lines = content.split("\n")
    lower = header.lower()
    for i, line in enumerate(lines):
        if ":" in line and line.split(":", 1)[0].strip().lower() == lower:
            lines[i] = f"{header}: {value}"
            return "\n".join(lines)
    # Header not found — insert after first header block
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip() == "":
            insert_at = i
            break
        insert_at = i + 1
    lines.insert(insert_at, f"{header}: {value}")
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via tmpfile + rename to avoid corruption on crash."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    # shutil.move on same filesystem is os.rename → atomic
    shutil.move(str(tmp), str(path))


def validate_draft(path: Path) -> bool:
    """Check draft has required headers (To, Subject)."""
    to = extract_header(path, "To")
    subject = extract_header(path, "Subject")
    return bool(to and subject)


def queue_draft(path: Path) -> Path:
    """Move draft to queue/new/. Detects profile from path."""
    cfg = get_config()
    # Find which profile this draft belongs to
    prof = ""
    rel = str(path.relative_to(cfg.maildir)) if path.is_relative_to(cfg.maildir) else ""
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] in cfg.profiles:
        prof = parts[0]
    queue_new = cfg.profile_path(prof, "queue") / "new"
    queue_new.mkdir(parents=True, exist_ok=True)
    dest = queue_new / path.name
    shutil.move(str(path), str(dest))
    return dest
