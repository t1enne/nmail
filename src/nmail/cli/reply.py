"""nmail reply — reply to a message."""

from __future__ import annotations

import click

from ..config import get_config
from ..drafts import create_draft, queue_draft, validate_draft
from ..headers import extract_body, extract_header
from ..logging import log_event
from ..notmuch import resolve_id
from ..shared import _open_editor, _set_header


@click.command()
@click.option("--all", "reply_all", is_flag=True)
@click.option("--template", "tmpl", default="reply")
@click.option("--no-quote", is_flag=True)
@click.argument("id")
def reply(reply_all: bool, tmpl: str, no_quote: bool, id: str) -> None:
    """Reply to a message.

    Opens editor with headers and quoted original pre-filled.
    On save, the draft is validated and queued for sending.

    Examples:

    nmail reply 182
    nmail reply --all 182
    nmail reply --no-quote 182
    nmail reply --template quick 182
    """
    path = resolve_id(id)
    if not path:
        click.echo(f"nmail reply: message not found: {id}", err=True)
        raise SystemExit(1)

    orig_from = extract_header(path, "From") or ""
    orig_subject = extract_header(path, "Subject") or "Re: "
    orig_msgid = extract_header(path, "Message-ID") or ""
    orig_refs = extract_header(path, "References") or ""
    orig_to = extract_header(path, "To") or ""
    orig_cc = extract_header(path, "Cc") or ""
    my_addr = get_config().from_address or ""

    if reply_all:
        recipients = _collect_reply_recipients(orig_from, orig_to, orig_cc, my_addr)
        to = ", ".join(recipients)
    else:
        to = orig_from

    refs = orig_refs.strip()
    if orig_msgid:
        refs = f"{refs} {orig_msgid}".strip()

    subject = orig_subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    draft_path = create_draft(tmpl, to=to, subject=subject)
    content = draft_path.read_text()
    content = _set_header(content, "In-Reply-To", orig_msgid)
    content = _set_header(content, "References", refs)
    if not no_quote:
        body = extract_body(path)
        quoted = "\n".join(f"> {line}" for line in body.split("\n"))
        content += f"\n\n{quoted}\n"
    draft_path.write_text(content)

    _open_editor(draft_path)
    if validate_draft(draft_path):
        queue_draft(draft_path)
        log_event("mail:draft", str(draft_path))
        click.echo(f"Queued: {draft_path.name}")
    else:
        click.echo(f"Draft saved (not queued — missing To/Subject): {draft_path}")


def _collect_reply_recipients(from_addr: str, to: str, cc: str, my_addr: str) -> list[str]:
    recipients: list[str] = []
    seen: set[str] = {my_addr.lower()}
    for addr in from_addr.split(","):
        a = addr.strip()
        if a.lower() not in seen:
            recipients.append(a)
            seen.add(a.lower())
    for addr in to.split(","):
        a = addr.strip()
        if a and a.lower() not in seen:
            recipients.append(a)
            seen.add(a.lower())
    for addr in cc.split(","):
        a = addr.strip()
        if a and a.lower() not in seen:
            recipients.append(a)
            seen.add(a.lower())
    return recipients
