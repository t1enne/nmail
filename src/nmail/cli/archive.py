"""nmail archive — move messages to archive."""

from __future__ import annotations

import click

from ..logging import log_event
from ..maildir import maildir_transfer
from ..shared import _resolve_ids


@click.command()
@click.argument("ids", nargs=-1)
def archive(ids: tuple[str, ...]) -> None:
    """Move messages to archive.

    Moves from incoming/ to archive/cur/.

    Examples:

    nmail archive 182 193
    nmail search --format ids tag:todo | nmail archive -
    """
    if not ids:
        raise click.UsageError("archive requires at least one message ID")
    files = _resolve_ids(ids)
    for f in files:
        maildir_transfer(f, "archive")
        click.echo(f"Archived: {f.name}")
    log_event("mail:archive", str(len(files)))
