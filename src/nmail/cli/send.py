"""nmail send — send queued messages via SMTP."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import click

from ..config import get_config
from ..logging import log_event
from ..maildir import maildir_transfer
from ..render import render_message


@click.command()
@click.option("--dry-run", is_flag=True)
@click.option("--id", "msg_id", default=None)
@click.option("--retry", type=int, default=1)
@click.option("--all", "send_all", is_flag=True)
def send(dry_run: bool, msg_id: str | None, retry: int, send_all: bool) -> None:
    """Send queued messages via SMTP.

    Drains queue/new/ through msmtp (or configured SMTP command).
    Successful sends move to sent/, failures stay in queue/cur/.

    Examples:

    nmail send
    nmail send --dry-run
    nmail send --retry 3
    nmail send --id queue-abc123
    nmail send --all
    """
    cfg = get_config()
    queue_dir = cfg.maildir / "queue"
    to_send: list[Path] = []
    if msg_id:
        for sf in ("new", "cur"):
            p = queue_dir / sf / msg_id
            if p.exists():
                to_send.append(p)
                break
    else:
        new_dir = queue_dir / "new"
        if new_dir.exists():
            to_send.extend(sorted(new_dir.iterdir(), key=lambda x: x.stat().st_mtime))
    if not to_send:
        click.echo("No messages to send.")
        return

    smtp_cmd = cfg.smtp_cmd
    if not shutil.which(smtp_cmd.split()[0]):
        click.echo(f"nmail send: SMTP command not found: {smtp_cmd}", err=True)
        raise SystemExit(1)

    sent = 0
    failed = 0
    for msg_path in to_send:
        rendered = render_message(msg_path, "mime")
        if dry_run:
            click.echo(f"Would send: {msg_path.name}")
            sent += 1
            continue
        ok = False
        for attempt in range(retry):
            try:
                proc = subprocess.run(
                    smtp_cmd.split(), input=rendered, capture_output=True, text=True, timeout=60
                )
                if proc.returncode == 0:
                    maildir_transfer(msg_path, "sent")
                    log_event("mail:sent", str(msg_path))
                    click.echo(f"Sent: {msg_path.name}")
                    sent += 1
                    ok = True
                    break
                if attempt < retry - 1:
                    time.sleep(2)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
                if attempt < retry - 1:
                    time.sleep(2)
        if not ok:
            _move_to_queue_cur(msg_path)
            log_event("mail:error", str(msg_path))
            click.echo(f"Failed: {msg_path.name}", err=True)
            failed += 1
    click.echo(f"Sent: {sent}, Failed: {failed}")


def _move_to_queue_cur(path: Path) -> None:
    from ..config import get_config

    cur = get_config().maildir / "queue" / "cur"
    cur.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(cur / path.name))
