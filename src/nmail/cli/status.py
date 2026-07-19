"""nmail status — mailbox statistics."""

from __future__ import annotations

import json
import time

import click

from ..config import get_config
from ..constants import INCOMING, MAILDIR_SUBDIRS
from ..maildir import maildir_list_new, maildir_total
from ..notmuch import notmuch_available, notmuch_count


@click.command()
@click.option("--json", "-j", "as_json", is_flag=True)
@click.option("--watch", "-w", "watch_mode", is_flag=True)
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
    cfg = get_config()
    profiles = cfg.profiles if cfg.profiles else [""]

    stats: dict[str, dict[str, dict[str, int]]] = {}
    flat_stats: dict[str, dict[str, int]] = {}

    for prof in profiles:
        profile_stats: dict[str, dict[str, int]] = {}
        for d in MAILDIR_SUBDIRS:
            path_key = f"{prof}/{d}" if prof else d
            profile_stats[d] = {
                "total": maildir_total(path_key),
                "new": len(maildir_list_new(path_key)),
            }
        # Include notmuch unread count
        if notmuch_available():
            # notmuch doesn't need profile path — it indexes everything
            unread = notmuch_count("tag:unread")
            profile_stats[INCOMING]["unread"] = unread

        if prof:
            stats[prof] = profile_stats
        else:
            flat_stats = profile_stats

    if as_json:
        click.echo(json.dumps(stats if profiles[0] else flat_stats))
    else:
        if profiles[0]:
            for prof_name, pstats in stats.items():
                click.echo(f"\n[{prof_name}]")
                for name, s in pstats.items():
                    line = f"  {name:12s}  {s['total']:4d} total  {s['new']:4d} new"
                    if "unread" in s:
                        line += f"  {s['unread']:4d} unread"
                    click.echo(line)
        else:
            for name, s in flat_stats.items():
                line = f"{name:12s}  {s['total']:4d} total  {s['new']:4d} new"
                if "unread" in s:
                    line += f"  {s['unread']:4d} unread"
                click.echo(line)
