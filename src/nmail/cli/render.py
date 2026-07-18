"""nmail render — render a draft to RFC5322 MIME format."""

from __future__ import annotations

from pathlib import Path

import click

from ..render import render_message


@click.command("render")
@click.option("--format", "fmt", type=click.Choice(["plain", "mime", "html"]), default="mime")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def render_cmd(fmt: str, file: Path) -> None:
    """Render a draft to RFC5322 MIME format.

    Converts Markdown draft with RFC822 headers to a proper MIME message.

    Examples:

    nmail render draft.md
    nmail render --format plain draft.md
    nmail render --format html draft.md
    nmail render queue/new/msg123
    """
    click.echo(render_message(file, fmt))
