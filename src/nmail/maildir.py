"""Maildir operations: move, flag, count, list."""

from __future__ import annotations

import contextlib
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Final

from .config import get_config
from .constants import MAILDIR_SUBDIRS, MAILDIR_SUBFOLDERS

logger = logging.getLogger(__name__)

# ── Maildir path helpers ─────────────────────────────────────────────────────

FLAG_MAP: Final = {"flagged": "F", "replied": "R", "seen": "S", "trashed": "T", "draft": "D"}

FLAG_REVERSE: Final = {v: k for k, v in FLAG_MAP.items()}


def ensure_maildir(profile: str | None = None) -> None:
    """Count messages in a maildir.

    directory can be:
      'incoming'        — flat-mode subdir
      'work/incoming'   — explicit profile/subdir
      'work'            — bare profile name (counts all subdirs)

    Note: If a profile name collides with a subdir name (e.g., a profile
    named 'incoming'), the profile branch wins. Avoid naming profiles
    after subdirs.
    """
    cfg = get_config()
    profiles: list[str] = []
    if profile:
        profiles = [profile]
    elif cfg.profiles:
        profiles = cfg.profiles
    else:
        profiles = [""]

    for prof in profiles:
        base = cfg.maildir / prof if prof else cfg.maildir
        for d in MAILDIR_SUBDIRS:
            for sf in MAILDIR_SUBFOLDERS:
                (base / d / sf).mkdir(parents=True, exist_ok=True)


def _parse_dir(directory: str) -> tuple[str, str]:
    """Parse 'profile/subdir' or 'subdir' into (profile, subdir)."""
    if "/" in directory:
        a, b = directory.split("/", 1)
        return (a, b)
    return ("", directory)


def maildir_move(src: Path, directory: str) -> Path:
    """Move file into a Maildir directory atomically (via tmp→new).

    directory can be 'incoming' (flat), 'work/incoming' (profile-relative),
    or 'personal/incoming'.
    """
    cfg = get_config()
    prof, sub = _parse_dir(directory)
    target = cfg.profile_path(prof, sub)
    dest_dir = target / "new"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    os.rename(src, dest)
    _refresh_notmuch()
    return dest


def maildir_new_id(host: str = "localhost", pid: int | None = None) -> str:
    """Generate unique Maildir filename."""
    ts = int(time.time())
    us = int((time.time() % 1) * 1_000_000)
    pid_val = pid if pid is not None else os.getpid()
    return f"{ts}.M{us}P{pid_val}.{host}"


def _flag_suffix(path: Path) -> str:
    """Extract the :2, part from a Maildir filename."""
    name = path.name
    m = re.search(r":2,([A-Z]*)$", name)
    return m.group(1) if m else ""


def _set_suffix(path: Path, flags: str) -> Path:
    name = path.name
    m = re.search(r"^(.*?)(:2,[A-Z]*)?$", name)
    base = m.group(1) if m else name
    new_name = f"{base}:2,{flags}" if flags else base
    return path.with_name(new_name)


def _refresh_notmuch() -> None:
    """Incrementally re-index notmuch after a file rename/move."""
    cfg = get_config()
    if not cfg.notmuch_enabled:
        return
    notmuch_cmd = cfg.notmuch_command
    with contextlib.suppress(Exception):
        subprocess.run(
            [notmuch_cmd, "new"],
            capture_output=True,
            timeout=30,
        )


def add_flag(path: Path, flag: str) -> Path:
    code = FLAG_MAP.get(flag, flag)
    current = set(_flag_suffix(path))
    current.add(code)
    new_flags = "".join(sorted(current))
    new_path = _set_suffix(path, new_flags)
    if new_path != path:
        os.rename(path, new_path)
        _refresh_notmuch()
    return new_path


def remove_flag(path: Path, flag: str) -> Path:
    code = FLAG_MAP.get(flag, flag)
    current = set(_flag_suffix(path))
    current.discard(code)
    new_flags = "".join(sorted(current))
    new_path = _set_suffix(path, new_flags)
    if new_path != path:
        os.rename(path, new_path)
        _refresh_notmuch()
    return new_path


def has_flag(path: Path, flag: str) -> bool:
    code = FLAG_MAP.get(flag, flag)
    return code in _flag_suffix(path)


def mark_read(path: Path) -> Path:
    """Move from new/ to cur/ and add seen flag."""
    if not path.is_file():
        return path
    cfg = get_config()
    # Check all profiles' new/ dirs
    profiles = cfg.profiles if cfg.profiles else [""]
    for prof in profiles:
        base = cfg.profile_path(prof)
        for subdir in MAILDIR_SUBDIRS:
            new_dir = base / subdir / "new"
            cur_dir = base / subdir / "cur"
            try:
                if path.relative_to(new_dir):
                    cur_dir.mkdir(parents=True, exist_ok=True)
                    dest = cur_dir / path.name
                    os.rename(path, dest)
                    _refresh_notmuch()
                    return add_flag(dest, "seen")
            except ValueError:
                continue
    _refresh_notmuch()
    return add_flag(path, "seen")


def maildir_count(directory: str) -> int:
    """Count messages in a maildir.

    directory can be 'incoming' (flat), 'work/incoming', or 'personal'.
    When a bare profile name is given (e.g. 'work'), counts all subdirs.
    """
    cfg = get_config()
    if "/" in directory:
        prof, sub = directory.split("/", 1)
        base = cfg.profile_path(prof, sub)
        new = len(list((base / "new").iterdir())) if (base / "new").exists() else 0
        cur = len(list((base / "cur").iterdir())) if (base / "cur").exists() else 0
        return new + cur
    # Bare profile name (e.g. 'work') or flat subdir (e.g. 'incoming')
    # Check if it's a profile
    if cfg.profiles and directory in cfg.profiles:
        total = 0
        for sub in MAILDIR_SUBDIRS:
            total += maildir_count(f"{directory}/{sub}")
        return total
    # Flat subdir
    d = cfg.maildir / directory
    new = len(list((d / "new").iterdir())) if (d / "new").exists() else 0
    cur = len(list((d / "cur").iterdir())) if (d / "cur").exists() else 0
    return new + cur


def maildir_list_new(directory: str) -> list[Path]:
    """List new messages. Supports 'profile/subdir' or bare subdir."""
    cfg = get_config()
    if "/" in directory:
        prof, sub = directory.split("/", 1)
        d = cfg.profile_path(prof, sub) / "new"
    else:
        d = cfg.maildir / directory / "new"
    if not d.exists():
        return []
    return sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)


def maildir_list_all(directory: str) -> list[Path]:
    """List all messages. Supports 'profile/subdir' or bare subdir."""
    cfg = get_config()
    if "/" in directory:
        prof, sub = directory.split("/", 1)
        base = cfg.profile_path(prof, sub)
    else:
        base = cfg.maildir / directory
    result: list[Path] = []
    for sf in ("new", "cur"):
        p = base / sf
        if p.exists():
            result.extend(p.iterdir())
    return sorted(result, key=lambda p: p.stat().st_mtime, reverse=True)


def maildir_total(directory: str) -> int:
    return maildir_count(directory)


def maildir_transfer(src: Path, dst_dir: str) -> Path:
    """Move message between Maildirs, preserving flags.

    dst_dir can be 'archive', 'sent', 'trash', 'personal/archive', etc.
    """
    flags = _flag_suffix(src)
    dest = maildir_move(src, dst_dir)
    if flags:
        dest = _set_suffix(dest, flags)
    return dest
