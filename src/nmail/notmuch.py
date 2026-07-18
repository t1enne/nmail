"""Notmuch integration with grep/rg fallback."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from pathlib import Path

from .config import get_config
from .maildir import MAILDIR_SUBDIRS


def _cmd(notmuch_cmd: str, *args: str) -> list[str]:
    return [notmuch_cmd, *args]


def notmuch_available() -> bool:
    cfg = get_config()
    notmuch_cmd = cfg.notmuch_command
    try:
        subprocess.run(
            [notmuch_cmd, "count", "*"],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _rg_search(query: str) -> list[str]:
    cfg = get_config()
    if not shutil.which("rg"):
        return _grep_search(query)
    files: list[str] = []
    for d in (INCOMING, ARCHIVE, SENT):
        p = cfg.maildir / d
        if p.exists():
            try:
                res = subprocess.run(
                    ["rg", "-l", "--no-messages", query, str(p)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                files.extend(res.stdout.strip().splitlines())
            except Exception:
                pass
    return files


def _grep_search(query: str) -> list[str]:
    cfg = get_config()
    files: list[str] = []
    for d in (INCOMING, ARCHIVE, SENT):
        p = cfg.maildir / d
        if p.exists():
            try:
                res = subprocess.run(
                    ["grep", "-rl", query, str(p)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                files.extend(res.stdout.strip().splitlines())
            except Exception:
                pass
    return files


def _fallback_search(query: str) -> list[str]:
    return _rg_search(query)


INCOMING = "incoming"
ARCHIVE = "archive"
SENT = "sent"


def notmuch_search(query: str, output: str = "files") -> list[str]:
    """Search with notmuch, falling back to ripgrep over Maildir."""
    cfg = get_config()
    if cfg.notmuch_enabled and notmuch_available():
        try:
            res = subprocess.run(
                [cfg.notmuch_command, "search", f"--output={output}", query],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return [line for line in res.stdout.strip().splitlines() if line]
        except Exception:
            pass
    return _fallback_search(query)


def notmuch_count(query: str) -> int:
    cfg = get_config()
    if cfg.notmuch_enabled and notmuch_available():
        try:
            res = subprocess.run(
                [cfg.notmuch_command, "count", query],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return int(res.stdout.strip() or 0)
        except Exception:
            pass
    return len(_fallback_search(query))


def notmuch_tag(op_tag: str, *ids: str) -> None:
    """Apply notmuch tag operation. op_tag like +todo or -unread."""
    cfg = get_config()
    if not cfg.notmuch_enabled or not notmuch_available():
        return
    with contextlib.suppress(Exception):
        subprocess.run(
            [cfg.notmuch_command, "tag", op_tag, *ids],
            capture_output=True,
            timeout=30,
        )


def notmuch_new() -> None:
    """Re-index notmuch."""
    cfg = get_config()
    if cfg.notmuch_enabled and notmuch_available():
        with contextlib.suppress(Exception):
            subprocess.run(
                [cfg.notmuch_command, "new"],
                capture_output=True,
                timeout=120,
            )


def _resolve_via_notmuch(id_str: str) -> Path | None:
    cfg = get_config()
    try:
        res = subprocess.run(
            [cfg.notmuch_command, "search", "--output=files", f"id:{id_str}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = [line for line in res.stdout.strip().splitlines() if line]
        if lines:
            return Path(lines[0])
    except Exception:
        pass
    return None


def resolve_id(id_str: str) -> Path | None:
    """Resolve a message ID or file path to a Maildir file."""
    path = Path(id_str).expanduser()
    if path.exists() and path.is_file():
        return path

    # Try notmuch first
    resolved = _resolve_via_notmuch(id_str)
    if resolved and resolved.exists():
        return resolved

    # Fallback: glob over Maildir
    cfg = get_config()
    for subdir in MAILDIR_SUBDIRS:
        d = cfg.maildir / subdir
        if d.exists():
            for p in d.rglob(f"{id_str}*"):
                if p.is_file():
                    return p
    return None
