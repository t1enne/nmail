"""nmail status — mailbox statistics."""

from __future__ import annotations

import json
import time

import click

from ..maildir import MAILDIR_SUBDIRS, maildir_list_new, maildir_total


@click.command()
@click.option("--json", "as_json", is_flag=True)
@click.option("--watch", "watch_mode", is_flag=True)
def status(as_json: bool, watch_mode: bool) -> None:
    """Show mailbox statistics.

    Examples:

    nmail status
    nmail status --json
    nmail status --watch
    """
    if watch_mode:
        while True:
            click.clear()
            _status_print(as_json)
            click.echo("\nRefreshing in 10s... (Ctrl-C to exit)")
            time.sleep(10)
    else:
        _status_print(as_json)


def _status_print(as_json: bool) -> None:
    stats = {
        d: {"total": maildir_total(d), "new": len(maildir_list_new(d))} for d in MAILDIR_SUBDIRS
    }
    if as_json:
        click.echo(json.dumps(stats))
    else:
        for name, s in stats.items():
            click.echo(f"{name:12s}  {s['total']:4d} total  {s['new']:4d} new")
