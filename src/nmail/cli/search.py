"""nmail search — search your mail."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import click

from ..notmuch import notmuch_search
from ..shared import _all_maildir_files


@click.command()
@click.option("--interactive/--no-interactive", default=False)
@click.option("--format", "fmt", type=click.Choice(["files", "ids", "json"]), default="files")
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
    try:
        proc = subprocess.run(
            ["fzf", "--multi"],
            input="\n".join(results),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            click.echo(proc.stdout.strip())
    except FileNotFoundError:
        click.echo("\n".join(results))


def _search_noninteractive(query: str, fmt: str, limit: int) -> None:
    results = notmuch_search(query) if query else _all_maildir_files()
    results = results[:limit]
    if fmt == "json":
        click.echo(json.dumps(results))
    elif fmt == "ids":
        for r in results:
            click.echo(Path(r).stem)
    else:
        for r in results:
            click.echo(r)
