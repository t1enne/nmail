"""nmail sync — sync mail from IMAP."""

from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click

from ..config import get_config
from ..logging import log_event
from ..maildir import ensure_maildir, maildir_count
from ..notmuch import notmuch_new


@click.command()
@click.option("--account", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--no-index", is_flag=True)
def sync(account: str | None, dry_run: bool, no_index: bool) -> None:
    """Sync mail from IMAP.

    Runs mbsync (or configured sync tool) to fetch new mail.
    Optionally re-indexes with notmuch.

    Examples:

    nmail sync
    nmail sync --account work
    nmail sync --dry-run
    nmail sync --no-index
    """
    cfg = get_config()
    ensure_maildir()
    log_event("mail:sync-start")
    before = maildir_count("incoming")

    sync_tool = cfg.sync_tool
    if not shutil.which(sync_tool):
        click.echo(f"nmail sync: sync tool not found: {sync_tool}", err=True)
        raise SystemExit(1)

    accounts = [account] if account else cfg.sync_accounts
    if not accounts:
        click.echo(
            "nmail sync: no accounts configured. Set sync.accounts in config.toml or use --account",
            err=True,
        )
        raise SystemExit(1)

    for acct in accounts:
        cmd = [sync_tool, acct]
        if dry_run:
            click.echo(f"Would run: {' '.join(cmd)}")
        else:
            try:
                subprocess.run(cmd, timeout=300)
            except subprocess.TimeoutExpired:
                log_event("mail:error", f"sync timeout: {acct}")
                click.echo(f"Sync timed out: {acct}", err=True)
                raise SystemExit(1) from None

    after = maildir_count("incoming")
    new_msgs = after - before
    if not no_index:
        notmuch_new()

    state_dir = Path.home() / ".local" / "state" / "nmail"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "last-sync").write_text(datetime.now(UTC).isoformat())
    log_event("mail:sync-end", str(new_msgs))
    click.echo(f"Sync complete. New: {new_msgs}")
