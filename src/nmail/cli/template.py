"""nmail template — manage draft templates."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ..config import get_config
from ..shared import _open_editor


@click.command()
@click.argument("operation", type=click.Choice(["list", "show", "edit", "create", "delete"]))
@click.argument("name", required=False)
def template(operation: str, name: str | None) -> None:
    """Manage draft templates.

    Templates in ~/Mail/templates/ are starting points for new drafts.
    Built-in: default, reply, forward.

    Examples:

    nmail template list
    nmail template show default
    nmail template create meeting
    nmail template edit reply
    nmail template delete obsolete
    cat template.md | nmail template create my-template
    """
    cfg = get_config()
    tmpl_dir = cfg.templates_dir
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    _ensure_default_templates(tmpl_dir)

    match operation:
        case "list":
            for p in sorted(tmpl_dir.glob("*.md")):
                click.echo(p.stem)
        case "show":
            if not name:
                raise click.UsageError("template show requires NAME")
            path = tmpl_dir / f"{name}.md"
            click.echo(path.read_text() if path.exists() else _not_found("Template", name))
        case "edit":
            if not name:
                raise click.UsageError("template edit requires NAME")
            path = tmpl_dir / f"{name}.md"
            if not path.exists():
                _not_found("Template", name)
            _open_editor(path)
        case "create":
            if not name:
                raise click.UsageError("template create requires NAME")
            path = tmpl_dir / f"{name}.md"
            if path.exists():
                click.echo(f"Template already exists: {name}", err=True)
                raise SystemExit(1)
            if not sys.stdin.isatty():
                path.write_text(sys.stdin.read())
            else:
                _open_editor(path)
            click.echo(f"Template created: {name}")
        case "delete":
            if not name:
                raise click.UsageError("template delete requires NAME")
            path = tmpl_dir / f"{name}.md"
            if path.exists():
                path.unlink()
                click.echo(f"Deleted: {name}")
            else:
                _not_found("Template", name)


def _ensure_default_templates(tmpl_dir: Path) -> None:
    defaults = {
        "default": "From: \nTo: \nCc: \nSubject:\n\n",
        "reply": "From: \nTo: \nCc: \nSubject:\n\n",
        "forward": "From: \nTo: \nCc: \nSubject:\n\n---\n\n",
    }
    for name, content in defaults.items():
        p = tmpl_dir / f"{name}.md"
        if not p.exists():
            p.write_text(content)


def _not_found(thing: str, name: str) -> None:
    click.echo(f"{thing} not found: {name}", err=True)
    raise SystemExit(1)
