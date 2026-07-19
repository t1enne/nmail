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

    Monitors incoming/new/ for each profile. Uses inotifywait if available,
    falls back to polling every 5 seconds.

    Examples:

    nmail watch
    nmail watch --once
    nmail watch --no-hooks
    """
    new_dirs = _new_dirs()

    if once:
        _watch_once(new_dirs)
        return

    if not _has_inotifywait():
        click.echo("nmail watch: inotifywait not found (install inotify-tools)", err=True)
        seen: set[str] = set()
        while True:
            _poll_maildir(new_dirs, seen, no_hooks)
            time.sleep(5)
    else:
        _inotify_watch(new_dirs, no_hooks)


def _new_dirs() -> list[Path]:
    cfg = get_config()
    profiles = cfg.profiles if cfg.profiles else [""]
    dirs: list[Path] = []
    for prof in profiles:
        d = cfg.profile_path(prof, "incoming") / "new"
        d.mkdir(parents=True, exist_ok=True)
        dirs.append(d)
    return dirs


def _has_inotifywait() -> bool:
    import shutil

    return shutil.which("inotifywait") is not None


def _watch_once(new_dirs: list[Path]) -> None:
    total = 0
    for d in new_dirs:
        count = len(list(d.iterdir())) if d.exists() else 0
        total += count
    click.echo(f"{total} new messages")


def _poll_maildir(new_dirs: list[Path], seen: set[str], no_hooks: bool) -> None:
    for d in new_dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if p.name not in seen:
                seen.add(p.name)
                click.echo(f"New: {p.name}")
                if not no_hooks:
                    log_event("mail:new", str(p))


def _inotify_watch(new_dirs: list[Path], no_hooks: bool) -> None:
    seen: set[str] = set()
    for d in new_dirs:
        if d.exists():
            for p in d.iterdir():
                seen.add(p.name)

    if not new_dirs:
        return

    try:
        # Watch all new/ dirs with inotifywait
        args = ["inotifywait", "-m", "-e", "create", "-e", "moved_to", "--format", "%f"]
        args.extend(str(d) for d in new_dirs)
        proc = subprocess.Popen(
            args,
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
                    log_event("mail:new", fname)
    except KeyboardInterrupt:
        pass
