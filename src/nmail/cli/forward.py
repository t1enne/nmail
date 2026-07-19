"""nmail forward — forward a message."""

from __future__ import annotations

import click

from ..drafts import create_draft, queue_draft, validate_draft
from ..headers import extract_body, extract_header
from ..logging import log_event
from ..notmuch import resolve_id
from ..shared import _open_editor


@click.command()
@click.option("--template", "-t", "tmpl", default="forward")
@click.argument("id")
def forward(tmpl: str, id: str) -> None:
    """Forward a message.

    Creates a new draft with the original message quoted as
    a forwarded block.

    Examples:

    nmail forward 182
    nmail forward --template simple 182
    """
    path = resolve_id(id)
    if not path:
        click.echo(f"nmail forward: message not found: {id}", err=True)
        raise SystemExit(1)

    orig_subject = extract_header(path, "Subject") or "Fwd: "
    orig_from = extract_header(path, "From") or ""
    orig_date = extract_header(path, "Date") or ""
    subject = orig_subject if orig_subject.lower().startswith("fwd:") else f"Fwd: {orig_subject}"

    draft_path = create_draft(tmpl, subject=subject)
    body = extract_body(path)
    fwd_block = (
        f"\n\n--- Forwarded message ---\n"
        f"From: {orig_from}\nDate: {orig_date}\nSubject: {orig_subject}\n\n{body}"
    )
    content = draft_path.read_text()
    draft_path.write_text(content + fwd_block + "\n")

    _open_editor(draft_path)
    if validate_draft(draft_path):
        queue_draft(draft_path)
        log_event("mail:draft", str(draft_path))
        click.echo(f"Queued: {draft_path.name}")
    else:
        click.echo(f"Draft saved: {draft_path}")
