"""Maildir operations: move, flag, count, list."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Final

from .config import get_config
from .constants import MAILDIR_SUBDIRS, MAILDIR_SUBFOLDERS

# ── Maildir path helpers ─────────────────────────────────────────────────────

FLAG_MAP: Final = {"flagged": "F", "replied": "R", "seen": "S", "trashed": "T", "draft": "D"}

FLAG_REVERSE: Final = {v: k for k, v in FLAG_MAP.items()}


def _maildir_sub(base: Path, sub: str) -> Path:
    return base / sub


def ensure_maildir() -> None:
    cfg = get_config()
    base = cfg.maildir
    for d in MAILDIR_SUBDIRS:
        for sf in MAILDIR_SUBFOLDERS:
            (base / d / sf).mkdir(parents=True, exist_ok=True)


def maildir_move(src: Path, dst_dir: str) -> Path:
    """Move file into a Maildir directory atomically (via tmp→new)."""
    cfg = get_config()
    target = cfg.maildir / dst_dir
    dest_dir = target / "new"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    # rename is atomic on same filesystem
    os.rename(src, dest)
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


def add_flag(path: Path, flag: str) -> Path:
    code = FLAG_MAP.get(flag, flag)
    current = set(_flag_suffix(path))
    current.add(code)
    new_flags = "".join(sorted(current))
    new_path = _set_suffix(path, new_flags)
    if new_path != path:
        os.rename(path, new_path)
    return new_path


def remove_flag(path: Path, flag: str) -> Path:
    code = FLAG_MAP.get(flag, flag)
    current = set(_flag_suffix(path))
    current.discard(code)
    new_flags = "".join(sorted(current))
    new_path = _set_suffix(path, new_flags)
    if new_path != path:
        os.rename(path, new_path)
    return new_path


def has_flag(path: Path, flag: str) -> bool:
    code = FLAG_MAP.get(flag, flag)
    return code in _flag_suffix(path)


def mark_read(path: Path) -> Path:
    """Move from new/ to cur/ and add seen flag."""
    if not path.is_file():
        return path
    cfg = get_config()
    for subdir in MAILDIR_SUBDIRS:
        new_dir = cfg.maildir / subdir / "new"
        cur_dir = cfg.maildir / subdir / "cur"
        try:
            if path.relative_to(new_dir):
                cur_dir.mkdir(parents=True, exist_ok=True)
                dest = cur_dir / path.name
                os.rename(path, dest)
                return add_flag(dest, "seen")
        except ValueError:
            continue
    return add_flag(path, "seen")


def maildir_count(directory: str) -> int:
    cfg = get_config()
    d = cfg.maildir / directory
    new = len(list((d / "new").iterdir())) if (d / "new").exists() else 0
    cur = len(list((d / "cur").iterdir())) if (d / "cur").exists() else 0
    return new + cur


def maildir_list_new(directory: str) -> list[Path]:
    cfg = get_config()
    d = cfg.maildir / directory / "new"
    if not d.exists():
        return []
    return sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)


def maildir_list_all(directory: str) -> list[Path]:
    cfg = get_config()
    d = cfg.maildir / directory
    result: list[Path] = []
    for sf in ("new", "cur"):
        p = d / sf
        if p.exists():
            result.extend(p.iterdir())
    return sorted(result, key=lambda p: p.stat().st_mtime, reverse=True)


def maildir_total(directory: str) -> int:
    return maildir_count(directory)


def maildir_transfer(src: Path, dst_dir: str) -> Path:
    """Move message between Maildirs, preserving flags."""
    flags = _flag_suffix(src)
    dest = maildir_move(src, dst_dir)
    if flags:
        dest = _set_suffix(dest, flags)
    return dest
