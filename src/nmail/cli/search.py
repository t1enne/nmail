"""nmail search — search your mail."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import click

from ..message import render_mail
from ..notmuch import notmuch_search
from ..shared import _all_maildir_files


@click.command()
@click.option("--interactive/--no-interactive", default=False)
@click.option(
    "--format", "fmt", type=click.Choice(["files", "ids", "json", "preview"]), default="preview"
)
@click.option("--limit", "-n", type=int, default=50)
@click.argument("query", required=False)
def search(interactive: bool, fmt: str, limit: int, query: str | None) -> None:
    """Search your mail.

    Uses notmuch for tagged/full-text search.
    Without notmuch, lists maildir files.

    Search syntax examples:

    nmail search tag:unread
    nmail search from:alice
    nmail search subject:invoice
    nmail search 'tag:unread from:alice'

    Output options:

    nmail search --interactive  # browse with fzf
    nmail search --format ids tag:todo   # IDs for piping
    nmail search --limit 20 from:bob
    """
    if interactive:
        _search_interactive(query or "")
    else:
        _search_noninteractive(query or "", fmt, limit)


def _search_interactive(query: str) -> None:
    results = notmuch_search(query) if query else _all_maildir_files()
    if not results:
        return
    if not shutil.which("fzf"):
        for p in results[:50]:
            click.echo(Path(p).stem)
        if len(results) > 50:
            click.echo(
                f"... and {len(results) - 50} more (install fzf for interactive browsing)", err=True
            )
        return

    # Pre-render all mails so fzf preview shows clean formatted output
    rendered: dict[str, str] = {}
    for p in results:
        try:
            rendered[p] = render_mail(Path(p))
        except Exception:
            rendered[p] = p

    preview_dir = Path(tempfile.gettempdir()) / f"nmail-previews-{uuid.uuid4().hex[:8]}"
    preview_dir.mkdir(exist_ok=True)
    for p in results:
        key = Path(p).name
        (preview_dir / f"{key}.md").write_text(rendered[p])

    with tempfile.NamedTemporaryFile(mode="w", suffix=".nmail", delete=False) as f:
        for p in results:
            f.write(p + "\n")
        tmp = f.name
    try:
        tty = os.open("/dev/tty", os.O_RDONLY)
        preview_script = f"fzf --multi --preview 'cat {preview_dir}/$(basename {{}}).md' < {tmp}"
        proc = subprocess.run(
            ["sh", "-c", preview_script],
            stdin=tty,
            stdout=subprocess.PIPE,
            text=True,
        )
        os.close(tty)
        if proc.returncode == 0:
            for line in proc.stdout.strip().splitlines():
                if line:
                    click.echo(Path(line).stem)
    finally:
        Path(tmp).unlink(missing_ok=True)
        shutil.rmtree(preview_dir, ignore_errors=True)


def _search_noninteractive(query: str, fmt: str, limit: int) -> None:
    results = notmuch_search(query) if query else _all_maildir_files()
    results = results[:limit]
    if fmt == "json":
        click.echo(json.dumps(results))
    elif fmt == "ids":
        for r in results:
            click.echo(Path(r).stem)
    elif fmt == "files":
        for r in results:
            click.echo(r)
    else:
        for r in results:
            click.echo(render_mail(Path(r)))
            click.echo("")
