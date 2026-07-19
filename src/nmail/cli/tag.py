"""nmail tag — add or remove notmuch tags."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ..config import get_config
from ..headers import extract_header
from ..logging import log_event
from ..notmuch import notmuch_tag


def _maildir_to_msgid(id_str: str) -> str | None:
    """Convert a Maildir filename stem to a notmuch message-ID by extracting
    the Message-ID header. Returns None if file can't be found/read."""
    cfg = get_config()
    for subdir in ("incoming", "archive", "sent"):
        for mdir_sub in ("cur", "new", "tmp"):
            d = cfg.maildir / subdir / mdir_sub
            if not d.exists():
                continue
            for p in d.glob(f"{id_str}*"):
                if not p.is_file():
                    continue
                mid = extract_header(p, "Message-ID")
                if mid:
                    return mid.strip("<>")
    return None


@click.command()
@click.argument("operation")
@click.argument("ids", nargs=-1)
def tag(operation: str, ids: tuple[str, ...]) -> None:
    """Add or remove notmuch tags.

    Operation must start with + (add) or - (remove).
    Reads IDs from stdin when - is given as ID.

    Examples:

    nmail tag +todo 182
    nmail tag -unread 182
    nmail tag +work 182 193 204
    nmail search --format ids from:bob | nmail tag +bob -
    """
    if not operation.startswith(("+", "-")):
        raise click.UsageError("Operation must start with + or -")
    if not ids:
        raise click.UsageError("No IDs provided")

    resolved: list[str] = []
    for id_str in ids:
        if id_str == "-":
            for line in sys.stdin:
                line = line.strip()
                if line:
                    resolved.append(line)
        else:
            resolved.append(id_str)

    cfg = get_config()
    for rid in resolved:
        if rid.startswith("id:") or "@" in rid:
            notmuch_tag(operation, rid)
        else:
            msgid = _maildir_to_msgid(rid)
            if msgid:
                notmuch_tag(operation, f"id:{msgid}")
            elif cfg.notmuch_enabled:
                click.echo(f"ID not found: {rid}", err=True)

    log_event("mail:tag", operation, str(len(resolved)))
