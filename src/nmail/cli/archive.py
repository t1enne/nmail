"""nmail archive — move messages to archive."""

from __future__ import annotations

import click

from ..config import get_config
from ..logging import log_event
from ..maildir import maildir_transfer
from ..shared import _detect_profile, _resolve_ids


@click.command()
@click.argument("ids", nargs=-1)
def archive(ids: tuple[str, ...]) -> None:
    """Move messages to archive.

    Detects profile from the message path. Moves to archive/cur/ within
    the same profile.

    Examples:

    nmail archive 182 193
    nmail search --format ids tag:todo | nmail archive -
    """
    if not ids:
        raise click.UsageError("archive requires at least one message ID or - for stdin")
    cfg = get_config()
    files = _resolve_ids(ids)
    for f in files:
        prof = _detect_profile(f, cfg)
        dst = f"{prof}/archive" if prof else "archive"
        maildir_transfer(f, dst)
        click.echo(f"Archived: {f.name}")
    log_event("mail:archive", str(len(files)))
