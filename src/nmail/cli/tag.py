"""nmail tag — add or remove notmuch tags."""

from __future__ import annotations

import subprocess
import sys

import click

from ..config import get_config
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

    # Warn on IDs that notmuch doesn't know about
    cfg = get_config()
    if cfg.notmuch_enabled:
        for rid in resolved:
            try:
                r = subprocess.run(
                    [cfg.notmuch_command, "search", "--output=files", f"id:{rid}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if not r.stdout.strip():
                    click.echo(f"ID not found: {rid}", err=True)
            except Exception:
                pass

    for rid in resolved:
        notmuch_tag(operation, rid)
    log_event("mail:tag", operation, str(len(resolved)))
