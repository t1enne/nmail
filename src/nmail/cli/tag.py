"""nmail tag — add or remove notmuch tags."""

from __future__ import annotations

import sys

import click

from ..logging import log_event
from ..notmuch import notmuch_tag


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
    for rid in resolved:
        notmuch_tag(operation, rid)
    log_event("mail:tag", operation, str(len(resolved)))
