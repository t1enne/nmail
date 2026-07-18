"""CLI subcommands — part 2: template, attach, archive, contacts, tag, trash, session, hook, watch, log."""  # noqa: E501

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import click

from .config import get_config
from .headers import extract_header
from .logging import log_event
from .maildir import (
    ensure_maildir,
    maildir_count,
    maildir_list_all,
    maildir_transfer,
)
from .notmuch import notmuch_new, notmuch_tag
from .shared import _open_editor, _resolve_ids

# ═══════════════════════════════════════════════════════════════════════════════
# template
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.argument("operation", type=click.Choice(["list", "show", "edit", "create", "delete"]))
@click.argument("name", required=False)
def template(operation: str, name: str | None) -> None:
    """Manage draft templates.

    Templates in ~/Mail/templates/ are starting points for
    new drafts. Built-in: default, reply, forward.

    Examples:

    nmail template list

    nmail template show default

    nmail template create meeting

    nmail template edit reply

    nmail template delete obsolete

    Create from stdin:

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


# ═══════════════════════════════════════════════════════════════════════════════
# attach
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.argument("operation", type=click.Choice(["list", "save", "open", "clean"]))
@click.argument("args", nargs=-1)
def attach(operation: str, args: tuple[str, ...]) -> None:
    """Manage saved attachments.

    Attachments stored in ~/Mail/attachments/. List, save
    to current directory, open, or clean.

    Examples:

    nmail attach list

    nmail attach save *.pdf  # copy to cwd

    nmail attach open invoice.pdf

    nmail attach clean  # remove all
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
                _not_found("Attachment", args[0])
        case "clean":
            for p in attach_dir.iterdir():
                p.unlink()
            click.echo("Attachments cleaned.")


# ═══════════════════════════════════════════════════════════════════════════════
# archive
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.argument("ids", nargs=-1)
def archive(ids: tuple[str, ...]) -> None:
    """Move messages to archive.

    Moves from incoming/ to archive/cur/.

    Examples:

    nmail archive 182 193

    Pipe from search:

    nmail search --format ids tag:todo | nmail archive -

    nmail search --format ids from:newsletter | nmail archive -
    """
    if not ids:
        raise click.UsageError("archive requires at least one message ID")
    files = _resolve_ids(ids)
    for f in files:
        maildir_transfer(f, "archive")
        click.echo(f"Archived: {f.name}")
    log_event("mail:archive", str(len(files)))


# ═══════════════════════════════════════════════════════════════════════════════
# contacts
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.option("--update", is_flag=True)
@click.option("--format", "fmt", type=click.Choice(["tsv", "json"]), default="tsv")
@click.argument("query", required=False)
def contacts(update: bool, fmt: str, query: str | None) -> None:
    """Search and manage contacts.

    Builds contact database from email headers (From, To, Cc).
    Cache at ~/.local/state/nmail/contacts.tsv.

    Examples:

    nmail contacts --update  # rebuild from all mail

    nmail contacts alice  # search

    nmail contacts --format json

    Interactive picker:

    nmail contacts | fzf | cut -f2 | xargs nmail compose --to
    """
    state_dir = Path.home() / ".local" / "state" / "nmail"
    state_dir.mkdir(parents=True, exist_ok=True)
    contacts_file = state_dir / "contacts.tsv"

    if update:
        _rebuild_contacts(contacts_file)
        click.echo(f"Contacts rebuilt: {contacts_file}")
        return
    if not contacts_file.exists():
        click.echo("No contacts cache. Run with --update first.", err=True)
        return

    entries = _read_contacts(contacts_file)
    if query:
        entries = [(n, e, c) for n, e, c in entries if query.lower() in f"{n} {e}".lower()]
    if fmt == "json":
        click.echo(json.dumps([{"name": n, "email": e, "count": c} for n, e, c in entries]))
    else:
        for name, email, count in entries:
            click.echo(f"{name}\t{email}\t{count}")


def _rebuild_contacts(path: Path) -> None:
    counter: dict[tuple[str, str], int] = {}
    for subdir in ("incoming", "archive", "sent"):
        for msg in maildir_list_all(subdir):
            for hdr in ("From", "To", "Cc"):
                val = extract_header(msg, hdr)
                if not val:
                    continue
                for addr in val.split(","):
                    addr = addr.strip()
                    if "<" in addr and ">" in addr:
                        name = addr[: addr.index("<")].strip().strip('"')
                        email = addr[addr.index("<") + 1 : addr.index(">")].strip()
                    else:
                        name = ""
                        email = addr
                    if email:
                        key = (name or email.split("@")[0], email.lower())
                        counter[key] = counter.get(key, 0) + 1
    with open(path, "w") as f:
        for (name, email), count in sorted(counter.items(), key=lambda x: -x[1]):
            f.write(f"{name}\t{email}\t{count}\n")


def _read_contacts(path: Path) -> list[tuple[str, str, int]]:
    result: list[tuple[str, str, int]] = []
    for line in path.read_text().strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            result.append((parts[0], parts[1], int(parts[2])))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# tag
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.argument("operation")
@click.argument("ids", nargs=-1)
def tag(operation: str, ids: tuple[str, ...]) -> None:
    """Add or remove notmuch tags.

    Operation must start with + (add) or - (remove).
    Reads IDs from stdin when - is given as ID.

    Requires notmuch.

    Examples:

    nmail tag +todo 182

    nmail tag -unread 182  # mark as read

    nmail tag +work 182 193 204

    Pipe from search:

    nmail search --format ids from:bob | nmail tag +bob -

    nmail search --format ids subject:report | nmail tag +report -
    """
    if not operation.startswith(("+", "-")):
        raise click.UsageError("Operation must start with + or -")
    if not ids:
        raise click.UsageError("No IDs provided")

    resolved: list[str] = []
    for id_str in ids:
        if id_str == "-":
            for line in sys.stdin:
                line = line.strip()
                if line:
                    resolved.append(line)
        else:
            resolved.append(id_str)
    for rid in resolved:
        notmuch_tag(operation, rid)
    log_event("mail:tag", operation, str(len(resolved)))


# ═══════════════════════════════════════════════════════════════════════════════
# trash
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.option("--empty", is_flag=True)
@click.option("--age", type=int, default=None)
@click.option("--force", is_flag=True)
@click.argument("ids", nargs=-1)
def trash(empty: bool, age: int | None, force: bool, ids: tuple[str, ...]) -> None:
    """Move messages to trash or manage trash.

    Three modes: move IDs to trash, empty trash entirely,
    or purge trash older than N days.

    Examples:

    nmail trash 182 193  # move to trash

    nmail trash --empty

    nmail trash --empty --force  # skip confirm

    nmail trash --age 30  # remove old trash

    nmail search --format ids subject:spam | nmail trash -
    """
    if empty:
        _empty_trash(force)
    elif age is not None:
        _purge_trash_by_age(age, force)
    else:
        if not ids:
            raise click.UsageError("trash requires message IDs, --empty, or --age")
        files = _resolve_ids(ids)
        for f in files:
            maildir_transfer(f, "trash")
            click.echo(f"Trashed: {f.name}")
        log_event("mail:trash", str(len(files)))


def _empty_trash(force: bool) -> None:
    cfg = get_config()
    trash_dir = cfg.maildir / "trash"
    count = maildir_count("trash")
    if count == 0:
        click.echo("Trash already empty.")
        return
    if not force and not click.confirm(f"Delete {count} messages in trash?"):
        return
    for sf in ("new", "cur"):
        d = trash_dir / sf
        if d.exists():
            for p in d.iterdir():
                p.unlink()
    log_event("mail:trash-empty", str(count))
    click.echo(f"Trash emptied ({count} messages).")


def _purge_trash_by_age(days: int, force: bool) -> None:
    cfg = get_config()
    trash_dir = cfg.maildir / "trash"
    cutoff = time.time() - (days * 86400)
    count = sum(
        1
        for sf in ("new", "cur")
        if (trash_dir / sf).exists()
        for p in (trash_dir / sf).iterdir()
        if p.stat().st_mtime < cutoff
    )
    if count == 0:
        click.echo(f"No trash older than {days} days.")
        return
    if not force and not click.confirm(f"Delete {count} messages older than {days} days?"):
        return
    deleted = 0
    for sf in ("new", "cur"):
        d = trash_dir / sf
        if d.exists():
            for p in d.iterdir():
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    deleted += 1
    log_event("mail:trash-purge", str(deleted), f"{days}d")
    click.echo(f"Purged {deleted} messages.")


# ═══════════════════════════════════════════════════════════════════════════════
# session
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.option("--no-sync", is_flag=True)
@click.option("--no-watch", is_flag=True)
@click.option("--layout", default=None)
def session(no_sync: bool, no_watch: bool, layout: str | None) -> None:
    """Launch the nmail tmux workspace.

    Creates (or re-attaches to) a tmux session. Grid layout:
    top: status + search  bottom: watcher (if enabled)

    Requires tmux.

    Examples:

    nmail session  # launch or attach

    nmail session --no-sync

    nmail session --no-watch

    nmail session --layout windows
    """
    cfg = get_config()
    tmux_cmd = cfg.tmux_command or "tmux"
    if not shutil.which(tmux_cmd):
        click.echo(f"nmail session: tmux not found ({tmux_cmd})", err=True)
        raise SystemExit(1)

    session_name = cfg.tmux_session
    chosen_layout = layout or cfg.tmux_layout

    try:
        subprocess.run(
            [tmux_cmd, "has-session", "-t", session_name],
            capture_output=True,
            timeout=5,
            check=True,
        )
        os.execvp(tmux_cmd, [tmux_cmd, "attach-session", "-t", session_name])
    except subprocess.CalledProcessError:
        pass  # Doesn't exist — create it

    ensure_maildir()
    if not no_sync:
        log_event("mail:sync-start")
        with contextlib.suppress(Exception):
            subprocess.run([cfg.sync_tool], timeout=300)
        notmuch_new()
        log_event("mail:sync-end")

    subprocess.run([tmux_cmd, "new-session", "-d", "-s", session_name, "-n", "mail"], check=True)

    if chosen_layout == "grid":
        _setup_grid(tmux_cmd, session_name, no_watch)
    else:
        _setup_window(tmux_cmd, session_name, no_watch)

    os.execvp(tmux_cmd, [tmux_cmd, "attach-session", "-t", session_name])


def _setup_grid(tmux_cmd: str, session: str, no_watch: bool) -> None:
    # Pane 1: status watcher (top-left)
    subprocess.run(
        [tmux_cmd, "send-keys", "-t", f"{session}:0.0", "nmail status --watch", "Enter"], check=True
    )
    # Pane 2: search (top-right)
    subprocess.run([tmux_cmd, "split-window", "-h", "-t", f"{session}:0.0"], check=True)
    subprocess.run(
        [tmux_cmd, "send-keys", "-t", f"{session}:0.1", "nmail search --interactive", "Enter"],
        check=True,
    )
    # Pane 3: compose area (bottom)
    subprocess.run([tmux_cmd, "split-window", "-v", "-t", f"{session}:0.0"], check=True)
    if not no_watch:
        subprocess.run(
            [tmux_cmd, "send-keys", "-t", f"{session}:0.2", "nmail watch", "Enter"], check=True
        )


def _setup_window(tmux_cmd: str, session: str, no_watch: bool) -> None:
    win = f"{session}:0"
    subprocess.run(
        [
            tmux_cmd,
            "send-keys",
            "-t",
            win,
            "nmail status; echo '[n]ew [s]earch [c]ompose [q]uit'",
            "Enter",
        ],
        check=True,
    )
    if not no_watch:
        subprocess.run([tmux_cmd, "split-window", "-v", "-t", win], check=True)
        subprocess.run(
            [tmux_cmd, "send-keys", "-t", f"{win}.1", "nmail watch", "Enter"], check=True
        )
        subprocess.run([tmux_cmd, "select-pane", "-t", f"{win}.0"], check=True)


# ═══════════════════════════════════════════════════════════════════════════════
# hook
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.argument("event")
@click.argument("args", nargs=-1)
def hook(event: str, args: tuple[str, ...]) -> None:
    """Manually trigger a hook event.

    Fires matching scripts in ~/.config/nmail/hooks.d/.
    Prefixed with 'mail:' if not already.

    Examples:

    nmail hook new 3  # simulate 3 new messages

    nmail hook sent queue-abc123

    nmail hook error queue-abc123 "SMTP timeout"
    """
    if not event.startswith("mail:"):
        event = f"mail:{event}"
    log_event(event, *args)


# ═══════════════════════════════════════════════════════════════════════════════
# watch
# ═══════════════════════════════════════════════════════════════════════════════


@click.command()
@click.option("--once", is_flag=True)
@click.option("--no-hooks", is_flag=True)
def watch(once: bool, no_hooks: bool) -> None:
    """Watch Maildir for new mail and fire events.

    Monitors incoming/new/. Uses inotifywait if available,
    falls back to polling every 5 seconds.

    Examples:

    nmail watch  # run continuously

    nmail watch --once  # check and exit

    nmail watch --no-hooks
    """
    cfg = get_config()
    maildir = cfg.maildir

    if once:
        _watch_once(maildir)
        return

    # inotify-based watching
    if not shutil.which("inotifywait"):
        click.echo("nmail watch: inotifywait not found (install inotify-tools)", err=True)
        # Fallback to polling
        seen: set[str] = set()
        while True:
            _poll_maildir(maildir, seen, no_hooks)
            time.sleep(5)
    else:
        _inotify_watch(maildir, no_hooks)


def _watch_once(maildir: Path) -> None:
    new_dir = maildir / "incoming" / "new"
    count = len(list(new_dir.iterdir())) if new_dir.exists() else 0
    click.echo(f"{count} new messages")


def _poll_maildir(maildir: Path, seen: set[str], no_hooks: bool) -> None:
    new_dir = maildir / "incoming" / "new"
    if not new_dir.exists():
        return
    for p in new_dir.iterdir():
        if p.name not in seen:
            seen.add(p.name)
            click.echo(f"New: {p.name}")
            if not no_hooks:
                log_event("mail:new", str(p))


def _inotify_watch(maildir: Path, no_hooks: bool) -> None:
    seen: set[str] = set()
    # Prime seen set
    new_dir = maildir / "incoming" / "new"
    if new_dir.exists():
        for p in new_dir.iterdir():
            seen.add(p.name)

    incoming_new = str(maildir / "incoming" / "new")
    if not Path(incoming_new).exists():
        Path(incoming_new).mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.Popen(
            ["inotifywait", "-m", "-e", "create", "-e", "moved_to", "--format", "%f", incoming_new],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            fname = line.decode().strip()
            if fname and fname not in seen:
                seen.add(fname)
                click.echo(f"New: {fname}")
                if not no_hooks:
                    log_event("mail:new", str(maildir / "incoming" / "new" / fname))
    except KeyboardInterrupt:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# log
# ═══════════════════════════════════════════════════════════════════════════════


@click.command("log")
@click.option("--follow", is_flag=True)
@click.option("--since", default=None)
@click.option("--level", default=None)
@click.option("--event", "event_filter", default=None)
@click.option("--json", "as_json", is_flag=True)
def log_cmd(
    follow: bool, since: str | None, level: str | None, event_filter: str | None, as_json: bool
) -> None:
    """View the activity log.

    nmail logs events as JSON lines to ~/Mail/logs/nmail.log.

    Examples:

    nmail log --follow  # tail -f

    nmail log --event mail:send

    nmail log --level error

    nmail log --since 2026-07-13

    Combine filters:

    nmail log --since 1h --level error

    nmail log --json | jq
    """
    cfg = get_config()
    log_file = cfg.logging_dir / "nmail.log"

    if follow:
        if log_file.exists():
            subprocess.run(["tail", "-f", str(log_file)])
        return

    if not log_file.exists():
        return

    entries = []
    for line in log_file.read_text().strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event_filter and entry.get("event") != event_filter:
            continue
        if level and entry.get("level", "").lower() != level.lower():
            continue
        if since:
            try:
                ts = datetime.fromisoformat(entry.get("ts", ""))
                since_dt = datetime.fromisoformat(since)
                if ts < since_dt:
                    continue
            except ValueError:
                pass
        entries.append(entry)

    if as_json:
        click.echo(json.dumps(entries, indent=2))
    else:
        for e in entries:
            click.echo(
                f"{e.get('ts', '')}  {e.get('event', ''):20s}  {' '.join(e.get('args', []))}"
            )
