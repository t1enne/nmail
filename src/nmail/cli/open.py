"""nmail open — open a message in your pager."""

from __future__ import annotations

import os

import click

from ..config import get_config
from ..headers import extract_headers_block
from ..maildir import mark_read
from ..notmuch import resolve_id


@click.command("open")
@click.option("--headers-only", is_flag=True)
@click.option("--raw", "raw_mode", is_flag=True)
@click.argument("id")
def open_cmd(headers_only: bool, raw_mode: bool, id: str) -> None:
    """Open a message in your pager.

    Resolves ID via notmuch or file listing. Marks as read
    (moves new/ to cur/). Uses bat if available.

    Examples:

    nmail open 182
    nmail open ~/Mail/incoming/new/...
    nmail open --headers-only 182
    nmail open --raw 182
    """
    path = resolve_id(id)
    if not path:
        click.echo(f"nmail open: message not found: {id}", err=True)
        raise SystemExit(1)
    mark_read(path)
    if raw_mode:
        click.echo(path.read_text(errors="replace"))
    elif headers_only:
        click.echo(extract_headers_block(path))
    else:
        cfg = get_config()
        if os.path.exists("/usr/bin/bat") or os.path.exists("/usr/local/bin/bat"):
            os.execvp("bat", ["bat", "-l", "email", str(path)])
        else:
            os.execvp(cfg.pager, [cfg.pager, str(path)])
