"""nmail trash — move messages to trash or manage trash."""

from __future__ import annotations

import time

import click

from ..config import get_config
from ..logging import log_event
from ..maildir import add_flag, maildir_count, maildir_transfer
from ..shared import _detect_profile, _resolve_ids


@click.command()
@click.option("--empty", is_flag=True)
@click.option("--age", type=int, default=None)
@click.option("--force", "-f", is_flag=True)
@click.argument("ids", nargs=-1)
def trash(empty: bool, age: int | None, force: bool, ids: tuple[str, ...]) -> None:
    """Move messages to trash or manage trash.

    Three modes: move IDs to trash, empty trash entirely,
    or purge trash older than N days.

    Examples:

    nmail trash 182 193
    nmail trash --empty
    nmail trash --empty --force
    nmail trash --age 30
    nmail search --format ids subject:spam | nmail trash -
    """
    if empty:
        _empty_trash(force)
    elif age is not None:
        _purge_trash_by_age(age, force)
    else:
        if not ids:
            raise click.UsageError("trash requires message IDs, --empty, or --age")
        cfg = get_config()
        files = _resolve_ids(ids)
        for f in files:
            f = add_flag(f, "trashed")
            prof = _detect_profile(f, cfg)
            dst = f"{prof}/trash" if prof else "trash"
            maildir_transfer(f, dst)

        click.echo(f"Trashed {str(len(files))} mails")
        log_event("mail:trash", str(len(files)))


def _empty_trash(force: bool) -> None:
    cfg = get_config()
    profiles = cfg.profiles if cfg.profiles else [""]
    total = 0
    for prof in profiles:
        path_key = f"{prof}/trash" if prof else "trash"
        total += maildir_count(path_key)
    if total == 0:
        click.echo("Trash already empty.")
        return
    if not force and not click.confirm(f"Delete {total} messages in trash?"):
        return
    deleted = 0
    for prof in profiles:
        trash_dir = cfg.profile_path(prof, "trash") if prof else cfg.maildir / "trash"
        for sf in ("new", "cur"):
            d = trash_dir / sf
            if d.exists():
                for p in d.iterdir():
                    p.unlink()
                    deleted += 1
    log_event("mail:trash-empty", str(deleted))
    click.echo(f"Trash emptied ({deleted} messages).")


def _purge_trash_by_age(days: int, force: bool) -> None:
    cfg = get_config()
    profiles = cfg.profiles if cfg.profiles else [""]
    cutoff = time.time() - (days * 86400)

    # Count old messages
    total = 0
    for prof in profiles:
        trash_dir = cfg.profile_path(prof, "trash") if prof else cfg.maildir / "trash"
        for sf in ("new", "cur"):
            d = trash_dir / sf
            if d.exists():
                for p in d.iterdir():
                    if p.stat().st_mtime < cutoff:
                        total += 1

    if total == 0:
        click.echo(f"No trash older than {days} days.")
        return
    if not force and not click.confirm(f"Delete {total} messages older than {days} days?"):
        return

    deleted = 0
    for prof in profiles:
        trash_dir = cfg.profile_path(prof, "trash") if prof else cfg.maildir / "trash"
        for sf in ("new", "cur"):
            d = trash_dir / sf
            if d.exists():
                for p in d.iterdir():
                    if p.stat().st_mtime < cutoff:
                        p.unlink()
                        deleted += 1
    log_event("mail:trash-purge", str(deleted), f"{days}d")
    click.echo(f"Purged {deleted} messages.")
