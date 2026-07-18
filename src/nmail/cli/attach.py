"""nmail attach — manage saved attachments."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from ..config import get_config


@click.command()
@click.argument("operation", type=click.Choice(["list", "save", "open", "clean"]))
@click.argument("args", nargs=-1)
def attach(operation: str, args: tuple[str, ...]) -> None:
    """Manage saved attachments.

    Attachments stored in ~/Mail/attachments/.

    Examples:

    nmail attach list
    nmail attach save *.pdf
    nmail attach open invoice.pdf
    nmail attach clean
    """
    cfg = get_config()
    attach_dir = cfg.maildir / "attachments"
    attach_dir.mkdir(parents=True, exist_ok=True)

    match operation:
        case "list":
            for p in sorted(attach_dir.iterdir()):
                click.echo(f"{p.name}  ({p.stat().st_size} bytes)")
        case "save":
            if not args:
                raise click.UsageError("attach save requires file patterns")
            for pattern in args:
                for p in sorted(attach_dir.glob(pattern)):
                    dest = Path.cwd() / p.name
                    shutil.copy2(p, dest)
                    click.echo(f"Saved: {dest}")
        case "open":
            if not args:
                raise click.UsageError("attach open requires a filename")
            path = attach_dir / args[0]
            if path.exists():
                click.launch(str(path))
            else:
                click.echo(f"Attachment not found: {args[0]}", err=True)
                raise SystemExit(1)
        case "clean":
            for p in attach_dir.iterdir():
                p.unlink()
            click.echo("Attachments cleaned.")
