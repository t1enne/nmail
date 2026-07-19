"""nmail watch — watch Maildir for new mail and fire events."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import click

from ..config import get_config
from ..logging import log_event


@click.command()
@click.option("--once", "-1", is_flag=True)
@click.option("--no-hooks", is_flag=True)
def watch(once: bool, no_hooks: bool) -> None:
    """Watch Maildir for new mail and fire events.

    Monitors incoming/new/. Uses inotifywait if available,
    falls back to polling every 5 seconds.

    Examples:

    nmail watch
    nmail watch --once
    nmail watch --no-hooks
    """
    cfg = get_config()
    maildir = cfg.maildir

    if once:
        _watch_once(maildir)
        return

    if not _has_inotifywait():
        click.echo("nmail watch: inotifywait not found (install inotify-tools)", err=True)
        seen: set[str] = set()
        while True:
            _poll_maildir(maildir, seen, no_hooks)
            time.sleep(5)
    else:
        _inotify_watch(maildir, no_hooks)


def _has_inotifywait() -> bool:
    import shutil

    return shutil.which("inotifywait") is not None


def _watch_once(maildir: Path) -> None:
    new_dir = maildir / "incoming" / "new"
    count = len(list(new_dir.iterdir())) if new_dir.exists() else 0
    click.echo(f"{count} new messages")


def _poll_maildir(maildir: Path, seen: set[str], no_hooks: bool) -> None:
    new_dir = maildir / "incoming" / "new"
    if not new_dir.exists():
        return
    for p in new_dir.iterdir():
        if p.name not in seen:
            seen.add(p.name)
            click.echo(f"New: {p.name}")
            if not no_hooks:
                log_event("mail:new", str(p))


def _inotify_watch(maildir: Path, no_hooks: bool) -> None:
    seen: set[str] = set()
    new_dir = maildir / "incoming" / "new"
    if new_dir.exists():
        for p in new_dir.iterdir():
            seen.add(p.name)

    incoming_new = str(maildir / "incoming" / "new")
    if not Path(incoming_new).exists():
        Path(incoming_new).mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.Popen(
            ["inotifywait", "-m", "-e", "create", "-e", "moved_to", "--format", "%f", incoming_new],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            fname = line.decode().strip()
            if fname and fname not in seen:
                seen.add(fname)
                click.echo(f"New: {fname}")
                if not no_hooks:
                    log_event("mail:new", str(maildir / "incoming" / "new" / fname))
    except KeyboardInterrupt:
        pass
