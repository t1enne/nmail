"""nmail search — search your mail."""

from __future__ import annotations

import atexit
import json
import os
import re
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
    "--format",
    "fmt",
    type=click.Choice(["files", "ids", "json", "preview", "summary"]),
    default="summary",
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
    nmail search --format summary tag:unread  # one-line per message
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
    atexit.register(shutil.rmtree, preview_dir, ignore_errors=True)
    for p in results:
        key = Path(p).name
        (preview_dir / f"{key}.md").write_text(rendered[p])

    try:
        tty_fd = os.open("/dev/tty", os.O_RDONLY)
    except OSError:
        click.echo("interactive mode requires a terminal", err=True)
        raise SystemExit(1) from None

    with tempfile.NamedTemporaryFile(mode="w", suffix=".nmail", delete=False) as f:
        for p in results:
            f.write(p + "\n")
        tmp = f.name
    try:
        preview_script = f"fzf --multi --preview 'cat {preview_dir}/$(basename {{}}).md' < {tmp}"
        proc = subprocess.run(
            ["sh", "-c", preview_script],
            stdin=tty_fd,
            stdout=subprocess.PIPE,
            text=True,
        )
        if proc.returncode == 0:
            for line in proc.stdout.strip().splitlines():
                if line:
                    click.echo(Path(line).stem)
    finally:
        os.close(tty_fd)
        Path(tmp).unlink(missing_ok=True)
        shutil.rmtree(preview_dir, ignore_errors=True)


# ── Summary format helpers ────────────────────────────────────────────────

_FROM_RE = re.compile(r"^From:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_SUBJECT_RE = re.compile(r"^Subject:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_DATE_RE = re.compile(r"^Date:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def _summary_line(path: Path) -> str:
    """One-line summary: date  from  subject."""
    try:
        raw = path.read_text(errors="replace")
    except Exception:
        return f"{path.name}: (unreadable)"
    m = _DATE_RE.search(raw)
    date = m.group(1).strip() if m else ""
    m = _FROM_RE.search(raw)
    fro = m.group(1).strip() if m else "?"
    m = _SUBJECT_RE.search(raw)
    subj = m.group(1).strip() if m else "(no subject)"
    # shorten date like "Fri, 17 Jul 2026" -> "Jul 17"
    date_short = _truncate_date(date)
    # shorten long subjects
    if len(subj) > 72:
        subj = subj[:69] + "..."
    return f"{date_short:12s}  {fro:<30.30s}  {subj}"


def _truncate_date(raw: str) -> str:
    """Take a date string, return a short friendly form."""
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S %z",
        "%a, %d %b %Y",
    ):
        try:
            import datetime

            parsed = datetime.datetime.strptime(raw.strip(), fmt)
            return parsed.strftime("%b %d")
        except ValueError:
            continue
    # Relative for today/yesterday
    if "Today" in raw:
        return "Today"
    if "Yest." in raw:
        return "Yest."
    return raw[:10] if len(raw) > 10 else raw


def _print_summary(paths: list[str]) -> None:
    for r in paths:
        p = Path(r)
        if not p.exists() or not p.is_file():
            continue
        click.echo(_summary_line(p))


def _search_noninteractive(query: str, fmt: str, limit: int) -> None:
    raw = notmuch_search(query) if query else _all_maildir_files()
    total = len(raw)
    results = raw[:limit]

    if not results:
        click.echo("No results.", err=True)
        return

    if total > limit:
        click.echo(f"{total} results (showing first {limit})", err=True)
    else:
        click.echo(f"{total} results", err=True)

    if fmt == "json":
        click.echo(json.dumps(results))
    elif fmt == "ids":
        for r in results:
            click.echo(Path(r).stem)
    elif fmt == "files":
        for r in results:
            click.echo(r)
    elif fmt == "summary":
        _print_summary(results)
    else:
        for r in results:
            rendered = render_mail(Path(r))
            if rendered:
                click.echo(rendered)
                click.echo("")
