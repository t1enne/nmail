"""nmail session — launch the nmail tmux workspace."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess

import click

from ..config import get_config
from ..logging import log_event
from ..maildir import ensure_maildir
from ..notmuch import notmuch_new


@click.command()
@click.option("--no-sync", is_flag=True)
@click.option("--no-watch", is_flag=True)
@click.option("--layout", default=None)
def session(no_sync: bool, no_watch: bool, layout: str | None) -> None:
    """Launch the nmail tmux workspace.

    Creates (or re-attaches to) a tmux session with status/search layout.

    Examples:

    nmail session
    nmail session --no-sync
    nmail session --no-watch
    nmail session --layout windows
    """
    cfg = get_config()
    tmux_cmd = cfg.tmux_command or "tmux"
    if not shutil.which(tmux_cmd):
        click.echo(f"nmail session: tmux not found ({tmux_cmd})", err=True)
        raise SystemExit(1)

    session_name = cfg.tmux_session
    chosen_layout = layout or cfg.tmux_layout

    try:
        subprocess.run(
            [tmux_cmd, "has-session", "-t", session_name],
            capture_output=True,
            timeout=5,
            check=True,
        )
        os.execvp(tmux_cmd, [tmux_cmd, "attach-session", "-t", session_name])
    except subprocess.CalledProcessError:
        pass  # doesn't exist — create it

    ensure_maildir()
    if not no_sync:
        log_event("mail:sync-start")
        with contextlib.suppress(Exception):
            subprocess.run([cfg.sync_tool], timeout=300)
        notmuch_new()
        log_event("mail:sync-end")

    subprocess.run([tmux_cmd, "new-session", "-d", "-s", session_name, "-n", "mail"], check=True)

    if chosen_layout == "grid":
        _setup_grid(tmux_cmd, session_name, no_watch)
    else:
        _setup_window(tmux_cmd, session_name, no_watch)

    os.execvp(tmux_cmd, [tmux_cmd, "attach-session", "-t", session_name])


def _setup_grid(tmux_cmd: str, session: str, no_watch: bool) -> None:
    subprocess.run(
        [tmux_cmd, "send-keys", "-t", f"{session}:0.0", "nmail status --watch", "Enter"],
        check=True,
    )
    subprocess.run([tmux_cmd, "split-window", "-h", "-t", f"{session}:0.0"], check=True)
    subprocess.run(
        [tmux_cmd, "send-keys", "-t", f"{session}:0.1", "nmail search --interactive", "Enter"],
        check=True,
    )
    subprocess.run([tmux_cmd, "split-window", "-v", "-t", f"{session}:0.0"], check=True)
    if not no_watch:
        subprocess.run(
            [tmux_cmd, "send-keys", "-t", f"{session}:0.2", "nmail watch", "Enter"], check=True
        )


def _setup_window(tmux_cmd: str, session: str, no_watch: bool) -> None:
    win = f"{session}:0"
    subprocess.run(
        [
            tmux_cmd,
            "send-keys",
            "-t",
            win,
            "nmail status; echo '[n]ew [s]earch [c]ompose [q]uit'",
            "Enter",
        ],
        check=True,
    )
    if not no_watch:
        subprocess.run([tmux_cmd, "split-window", "-v", "-t", win], check=True)
        subprocess.run(
            [tmux_cmd, "send-keys", "-t", f"{win}.1", "nmail watch", "Enter"], check=True
        )
        subprocess.run([tmux_cmd, "select-pane", "-t", f"{win}.0"], check=True)
