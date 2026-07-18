"""nmail compose — compose a new message."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ..constants import DEFAULT_TEMPLATE
from ..drafts import create_draft, queue_draft, validate_draft
from ..logging import log_event
from ..maildir import ensure_maildir
from ..shared import _open_editor


@click.command()
@click.option("--to", default=None)
@click.option("--cc", default=None)
@click.option("--bcc", default=None)
@click.option("--subject", default=None)
@click.option("--attach", "attachments", multiple=True)
@click.option("--no-send", is_flag=True)
@click.option("--queue", "force_queue", is_flag=True)
@click.option("--stdin", "from_stdin", is_flag=True)
@click.argument("draft_arg", required=False)
def compose(
    to: str | None,
    cc: str | None,
    bcc: str | None,
    subject: str | None,
    attachments: tuple[str, ...],
    no_send: bool,
    force_queue: bool,
    from_stdin: bool,
    draft_arg: str | None,
) -> None:
    """Compose a new message.

    Opens $EDITOR on a Markdown draft. Headers in RFC822 style above
    "---" line. Body is Markdown. On save, validates and queues.

    Examples:

    nmail compose
    nmail compose --to alice@example.com
    nmail compose --to alice --subject "Meeting"
    nmail compose --no-send
    nmail compose meeting
    echo -e "To: a@b\\nSubject: hi\\n---\\n\\nHello" | nmail compose --stdin
    """
    ensure_maildir()
    if draft_arg and Path(draft_arg).exists():
        draft_path = Path(draft_arg)
    elif draft_arg:
        draft_path = create_draft(draft_arg, to=to, subject=subject, cc=cc, bcc=bcc)
    else:
        draft_path = create_draft(DEFAULT_TEMPLATE, to=to, subject=subject, cc=cc, bcc=bcc)

    if attachments:
        content = draft_path.read_text()
        content += "\n---\n" + "\n".join(attachments) + "\n"
        draft_path.write_text(content)
    if from_stdin:
        draft_path.write_text(sys.stdin.read())
    else:
        _open_editor(draft_path)

    if no_send:
        click.echo(f"Draft saved: {draft_path}")
    elif validate_draft(draft_path):
        queue_draft(draft_path)
        log_event("mail:draft", str(draft_path))
        click.echo(f"Queued: {draft_path.name}")
    else:
        click.echo(f"Draft saved (not queued — missing To/Subject): {draft_path}")
