"""CLI subcommands — part 1: search, reply, compose, send, forward, open, sync, status, render."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import click

from .config import get_config
from .constants import DEFAULT_TEMPLATE
from .drafts import create_draft, queue_draft, validate_draft
from .headers import extract_body, extract_header, extract_headers_block
from .logging import log_event
from .maildir import (
    MAILDIR_SUBDIRS,
    ensure_maildir,
    maildir_count,
    maildir_list_new,
    maildir_total,
    maildir_transfer,
    mark_read,
)
from .notmuch import notmuch_new, notmuch_search, resolve_id
from .render import render_message
from .shared import _all_maildir_files, _open_editor, _set_header


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

    nmail search 'tag:unread from:alice'  # combined

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

    nmail reply 182  # reply to message 182

    nmail reply --all 182  # reply to all recipients

    nmail reply --no-quote 182

    nmail reply --template quick 182

    Pipe from search:

    nmail search tag:unread | head -1 | xargs nmail reply
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

    nmail compose   # interactive, opens editor

    nmail compose --to alice@example.com

    nmail compose --to alice --subject "Meeting"

    nmail compose --no-send  # keep as draft only

    nmail compose meeting  # start from 'meeting' template

    Non-interactive from stdin:

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


@click.command()
@click.option("--dry-run", is_flag=True)
@click.option("--id", "msg_id", default=None)
@click.option("--retry", type=int, default=1)
@click.option("--all", "send_all", is_flag=True)
def send(dry_run: bool, msg_id: str | None, retry: int, send_all: bool) -> None:
    """Send queued messages via SMTP.

    Drains queue/new/ through msmtp (or configured SMTP command).
    Successful sends move to sent/, failures stay in queue/cur/.

    Examples:

    nmail send  # send all pending

    nmail send --dry-run  # preview without sending

    nmail send --retry 3  # retry up to 3 times

    nmail send --id queue-abc123  # send specific message

    nmail send --all  # include previously failed
    """
    cfg = get_config()
    queue_dir = cfg.maildir / "queue"
    to_send: list[Path] = []
    if msg_id:
        for sf in ("new", "cur"):
            p = queue_dir / sf / msg_id
            if p.exists():
                to_send.append(p)
                break
    else:
        new_dir = queue_dir / "new"
        if new_dir.exists():
            to_send.extend(sorted(new_dir.iterdir(), key=lambda x: x.stat().st_mtime))
    if not to_send:
        click.echo("No messages to send.")
        return

    smtp_cmd = cfg.smtp_cmd
    if not shutil.which(smtp_cmd.split()[0]):
        click.echo(f"nmail send: SMTP command not found: {smtp_cmd}", err=True)
        raise SystemExit(1)

    sent = 0
    failed = 0
    for msg_path in to_send:
        rendered = render_message(msg_path, "mime")
        if dry_run:
            click.echo(f"Would send: {msg_path.name}")
            sent += 1
            continue
        ok = False
        for attempt in range(retry):
            try:
                proc = subprocess.run(
                    smtp_cmd.split(), input=rendered, capture_output=True, text=True, timeout=60
                )
                if proc.returncode == 0:
                    maildir_transfer(msg_path, "sent")
                    log_event("mail:sent", str(msg_path))
                    click.echo(f"Sent: {msg_path.name}")
                    sent += 1
                    ok = True
                    break
                if attempt < retry - 1:
                    time.sleep(2)
            except (subprocess.TimeoutExpired, Exception):
                if attempt < retry - 1:
                    time.sleep(2)
        if not ok:
            _move_to_queue_cur(msg_path)
            log_event("mail:error", str(msg_path))
            click.echo(f"Failed: {msg_path.name}", err=True)
            failed += 1
    click.echo(f"Sent: {sent}, Failed: {failed}")


def _move_to_queue_cur(path: Path) -> None:
    cur = get_config().maildir / "queue" / "cur"
    cur.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(cur / path.name))


@click.command()
@click.option("--template", "tmpl", default="forward")
@click.argument("id")
def forward(tmpl: str, id: str) -> None:
    """Forward a message.

    Creates a new draft with the original message quoted as
    a forwarded block.

    Examples:

    nmail forward 182

    nmail forward --template simple 182

    Pipe from search:

    nmail search subject:report | head -1 | xargs nmail forward
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


@click.command("open")
@click.option("--headers-only", is_flag=True)
@click.option("--raw", "raw_mode", is_flag=True)
@click.argument("id")
def open_cmd(headers_only: bool, raw_mode: bool, id: str) -> None:
    """Open a message in your pager.

    Resolves ID via notmuch or file listing. Marks as read
    (moves new/ to cur/). Uses bat if available.

    Examples:

    nmail open 182  # by ID

    nmail open ~/Mail/incoming/new/...  # by path

    nmail open --headers-only 182

    nmail open --raw 182
    """
    path = resolve_id(id)
    if not path:
        click.echo(f"nmail open: message not found: {id}", err=True)
        raise SystemExit(1)
    mark_read(path)
    if raw_mode:
        click.echo(path.read_text(errors="replace"))
    elif headers_only:
        click.echo(extract_headers_block(path))
    else:
        cfg = get_config()
        if shutil.which("bat"):
            os.execvp("bat", ["bat", "-l", "email", str(path)])
        else:
            os.execvp(cfg.pager, [cfg.pager, str(path)])


@click.command()
@click.option("--account", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--no-index", is_flag=True)
def sync(account: str | None, dry_run: bool, no_index: bool) -> None:
    """Sync mail from IMAP.

    Runs mbsync (or configured sync tool) to fetch new mail.
    Optionally re-indexes with notmuch.

    Requires mbsync configured in ~/.mbsyncrc.

    Examples:

    nmail sync  # sync all accounts

    nmail sync --account work  # sync specific account

    nmail sync --dry-run

    nmail sync --no-index  # skip notmuch re-index
    """
    cfg = get_config()
    ensure_maildir()
    log_event("mail:sync-start")
    before = maildir_count("incoming")

    sync_tool = cfg.sync_tool
    if not shutil.which(sync_tool):
        click.echo(f"nmail sync: sync tool not found: {sync_tool}", err=True)
        raise SystemExit(1)

    cmd = [sync_tool] + ([account] if account else [])
    if dry_run:
        click.echo(f"Would run: {' '.join(cmd)}")
    else:
        try:
            subprocess.run(cmd, timeout=300)
        except subprocess.TimeoutExpired:
            log_event("mail:error", "sync timeout")
            click.echo("Sync timed out", err=True)
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


@click.command()
@click.option("--json", "as_json", is_flag=True)
@click.option("--watch", "watch_mode", is_flag=True)
def status(as_json: bool, watch_mode: bool) -> None:
    """Show mailbox statistics.

    Displays counts for incoming, archive, sent, drafts,
    queue, and trash directories.

    Examples:

    nmail status  # plain text overview

    nmail status --json  # machine-readable

    nmail status --watch  # live-refresh mode
    """
    if watch_mode:
        while True:
            click.clear()
            _status_print(as_json)
            click.echo("\nRefreshing in 10s... (Ctrl-C to exit)")
            time.sleep(10)
    else:
        _status_print(as_json)


def _status_print(as_json: bool) -> None:
    stats = {
        d: {"total": maildir_total(d), "new": len(maildir_list_new(d))} for d in MAILDIR_SUBDIRS
    }
    if as_json:
        click.echo(json.dumps(stats))
    else:
        for name, s in stats.items():
            click.echo(f"{name:12s}  {s['total']:4d} total  {s['new']:4d} new")


@click.command("render")
@click.option("--format", "fmt", type=click.Choice(["plain", "mime", "html"]), default="mime")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def render_cmd(fmt: str, file: Path) -> None:
    """Render a draft to RFC5322 MIME format.

    Converts Markdown draft with RFC822 headers to
    a proper MIME message on stdout.

    Examples:

    nmail render draft.md  # default: multipart/alternative

    nmail render --format plain draft.md  # text/plain only

    nmail render --format html draft.md  # text/html only

    nmail render queue/new/msg123

    Pipe to other tools:

    nmail render draft.md | bat --language=email

    nmail render draft.md | aspell list  # check spelling
    """
    click.echo(render_message(file, fmt))
