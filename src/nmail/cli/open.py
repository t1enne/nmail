"""nmail open — open a message in your pager."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import click

from ..config import get_config
from ..headers import extract_headers_block
from ..maildir import mark_read
from ..message import render_mail
from ..shared import _resolve_ids


@click.command("open")
@click.option("--headers-only", "-H", is_flag=True)
@click.option("--raw", "-r", "raw_mode", is_flag=True)
@click.argument("ids", nargs=-1)
def open_cmd(headers_only: bool, raw_mode: bool, ids: tuple[str, ...]) -> None:
    """Open a message in your pager.

    Resolves IDs via notmuch or file listing. Marks as read
    (moves new/ to cur/). Uses bat if available.

    Examples:

    nmail open 182
    nmail open ~/Mail/incoming/new/...
    nmail open --headers-only 182
    nmail open --raw 182
    nmail search --format ids --limit 1 from:google | nmail open -
    """
    if not ids:
        raise click.UsageError("open requires at least one message ID")
    paths = _resolve_ids(ids)
    if not paths:
        click.echo("nmail open: no messages found", err=True)
        raise SystemExit(1)
    if len(paths) > 1:
        click.echo(f"nmail open: multiple messages ({len(paths)}), opening first", err=True)
    path = mark_read(paths[0])
    if raw_mode:
        click.echo(path.read_text(errors="replace"))
    elif headers_only:
        click.echo(extract_headers_block(path))
    else:
        rendered = render_mail(path)
        cfg = get_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(rendered)
            tmp = f.name
        try:
            if os.path.exists("/usr/bin/bat") or os.path.exists("/usr/local/bin/bat"):
                os.execvp("bat", ["bat", "-l", "markdown", tmp])
            else:
                os.execvp(cfg.pager, [cfg.pager, tmp])
        finally:
            Path(tmp).unlink(missing_ok=True)
