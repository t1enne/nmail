"""nmail log — view the activity log."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime

import click

from ..config import get_config


@click.command("log")
@click.option("--follow", is_flag=True)
@click.option("--since", default=None)
@click.option("--level", default=None)
@click.option("--event", "event_filter", default=None)
@click.option("--json", "as_json", is_flag=True)
def log_cmd(
    follow: bool, since: str | None, level: str | None, event_filter: str | None, as_json: bool
) -> None:
    """View the activity log.

    nmail logs events as JSON lines to ~/Mail/logs/nmail.log.

    Examples:

    nmail log --follow
    nmail log --event mail:send
    nmail log --level error
    nmail log --since 2026-07-13
    nmail log --since 1h --level error
    nmail log --json | jq
    """
    cfg = get_config()
    log_file = cfg.logging_dir / "nmail.log"

    if follow:
        if log_file.exists():
            subprocess.run(["tail", "-f", str(log_file)])
        return

    if not log_file.exists():
        return

    entries = []
    for line in log_file.read_text().strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event_filter and entry.get("event") != event_filter:
            continue
        if level and entry.get("level", "").lower() != level.lower():
            continue
        if since:
            try:
                ts = datetime.fromisoformat(entry.get("ts", ""))
                since_dt = datetime.fromisoformat(since)
                if ts < since_dt:
                    continue
            except ValueError:
                pass
        entries.append(entry)

    if as_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        for e in entries:
            click.echo(
                f"{e.get('ts', '')}  {e.get('event', ''):20s}  {' '.join(e.get('args', []))}"
            )
