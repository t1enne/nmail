"""Notmuch integration with grep/rg fallback."""

from __future__ import annotations

import contextlib
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from .config import get_config
from .constants import ARCHIVE, INCOMING, MAILDIR_SUBDIRS, SENT

logger = logging.getLogger(__name__)

# Notmuch prefixes that don't work in grep/rg fallback
_NOTMUCH_PREFIXES = re.compile(
    r"\b(subject|from|to|tag|folder|path|id|thread|attachment|mimetype):", re.IGNORECASE
)


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
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _search_dirs() -> list[Path]:
    """Get all profile maildir paths to search, or flat paths."""
    cfg = get_config()
    dirs: list[Path] = []
    profiles = cfg.profiles
    if profiles:
        for prof in profiles:
            for d in (INCOMING, ARCHIVE, SENT):
                p = cfg.profile_path(prof, d)
                if p.exists():
                    dirs.append(p)
    else:
        for d in (INCOMING, ARCHIVE, SENT):
            p = cfg.maildir / d
            if p.exists():
                dirs.append(p)
    return dirs


def _rg_search(query: str) -> list[str]:
    if not shutil.which("rg"):
        return _grep_search(query)
    files: list[str] = []
    for d in _search_dirs():
        if d.exists():
            try:
                res = subprocess.run(
                    ["rg", "-l", "--no-messages", query, str(d)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                files.extend(res.stdout.strip().splitlines())
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
    return files


def _grep_search(query: str) -> list[str]:
    files: list[str] = []
    for d in _search_dirs():
        if d.exists():
            try:
                res = subprocess.run(
                    ["grep", "-rl", query, str(d)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                files.extend(res.stdout.strip().splitlines())
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass
    return files


def _fallback_search(query: str) -> list[str]:
    if _NOTMUCH_PREFIXES.search(query):
        logger.warning(
            "Structured query '%s' contains notmuch prefixes (subject:, from:, tag:, etc.). "
            "Fallback grep/rg uses literal text match — results may be incomplete or empty. "
            "Install notmuch for full structured search.",
            query,
        )
    return _rg_search(query)


def _exclude_trash(paths: list[str]) -> list[str]:
    """Filter out any path whose parent directory contains 'trash' (case-insensitive)."""
    return [p for p in paths if "trash" not in os.path.dirname(p).lower().split(os.sep)]


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
            results = [line for line in res.stdout.strip().splitlines() if line]
            results = _exclude_trash(results)
            # Skip stale index entries
            results = [r for r in results if Path(r).is_file()]
            return results
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.warning("notmuch search failed, falling back to grep: %s", e)
    return _fallback_search(query)


def notmuch_count(query: str) -> int:
    cfg = get_config()
    if cfg.notmuch_enabled and notmuch_available():
        try:
            res = subprocess.run(
                [cfg.notmuch_command, "count", query, "and", "not", "folder:trash"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return int(res.stdout.strip() or 0)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError) as e:
            logger.warning("notmuch count failed, falling back to grep: %s", e)
    return len(_fallback_search(query))


def notmuch_tag(op_tag: str, *ids: str) -> None:
    """Apply notmuch tag operation. op_tag like +todo or -unread."""
    cfg = get_config()
    if not cfg.notmuch_enabled or not notmuch_available():
        return
    cmd = [cfg.notmuch_command, "tag", op_tag, "--", *ids]
    with contextlib.suppress(Exception):
        subprocess.run(cmd, capture_output=True, timeout=30)


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
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _glob_dirs() -> list[Path]:
    """Get all profile subdir paths for glob-based ID resolution."""
    cfg = get_config()
    dirs: list[Path] = []
    profiles = cfg.profiles if cfg.profiles else [""]
    for prof in profiles:
        base = cfg.profile_path(prof)
        for sub in MAILDIR_SUBDIRS:
            base_sub = base / sub
            if base_sub.exists():
                dirs.append(base_sub)
    return dirs


def resolve_id(id_str: str) -> Path | None:
    """Resolve a message ID or file path to a Maildir file."""
    path = Path(id_str).expanduser()
    if path.is_file():
        return path

    # Try notmuch first
    resolved = _resolve_via_notmuch(id_str)
    if resolved and resolved.is_file():
        return resolved

    # Fallback: glob over all profile maildirs
    for d in _glob_dirs():
        for p in d.rglob(f"{id_str}*"):
            if p.is_file():
                return p
    return None


def resolve_ids(ids: list[str]) -> list[Path]:
    """Resolve multiple IDs, skipping non-existent. Logs warnings."""
    resolved: list[Path] = []
    for id_str in ids:
        p = resolve_id(id_str)
        if p:
            resolved.append(p)
    return resolved
