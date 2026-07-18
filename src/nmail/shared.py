"""Shared utilities for CLI commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import get_config
from .notmuch import resolve_id


def _open_editor(path: Path) -> None:
    cfg = get_config()
    editor = cfg.editor
    subprocess.run([editor, str(path)])


def _set_header(content: str, header: str, value: str) -> str:
    lines = content.split("\n")
    lower = header.lower()
    for i, line in enumerate(lines):
        if ":" in line and line.split(":", 1)[0].strip().lower() == lower:
            lines[i] = f"{header}: {value}"
            return "\n".join(lines)
    # Not found — insert after last header line
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip() == "":
            insert_at = i
            break
        insert_at = i + 1
    lines.insert(insert_at, f"{header}: {value}")
    return "\n".join(lines)


def _all_maildir_files() -> list[str]:
    from .maildir import maildir_list_all

    files: list[str] = []
    for d in ("incoming", "archive", "sent"):
        for p in maildir_list_all(d):
            files.append(str(p))
    return files


def _resolve_ids(ids: tuple[str, ...]) -> list[Path]:
    import click

    files: list[Path] = []
    for id_str in ids:
        if id_str == "-":
            for line in sys.stdin:
                line = line.strip()
                if line:
                    p = resolve_id(line)
                    if p:
                        files.append(p)
        else:
            p = resolve_id(id_str)
            if p:
                files.append(p)
            else:
                click.echo(f"Message not found: {id_str}", err=True)
    return files
