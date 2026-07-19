"""nmail contacts — search and manage contacts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import click

from ..config import get_config
from ..headers import extract_header
from ..maildir import maildir_list_all
from ..message import decode_rfc2047


@click.command()
@click.option("--update", "-u", is_flag=True)
@click.option("--interactive/--no-interactive", "-i/--no-interactive", default=False)
@click.option("--format", "-f", "fmt", type=click.Choice(["tsv", "json", "email"]), default="tsv")
@click.argument("query", required=False)
def contacts(update: bool, interactive: bool, fmt: str, query: str | None) -> None:
    """Search and manage contacts.

    Builds contact database from email headers (From, To, Cc).
    Cache at ~/.local/state/nmail/contacts.tsv.

    Examples:

    nmail contacts --update
    nmail contacts alice
    nmail contacts --interactive
    nmail contacts --format json
    nmail contacts --format email alice   # prints email only (for scripts)
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

    if interactive:
        _contacts_interactive(entries)
        return

    if fmt == "json":
        click.echo(json.dumps([{"name": n, "email": e, "count": c} for n, e, c in entries]))
    elif fmt == "email":
        for _, email, _ in entries:
            click.echo(email)
    else:
        for name, email, count in entries:
            click.echo(f"{name:40}\t{email:40s}\t{count:2d}")


def _normalize_id(name: str, email: str) -> str:
    """Derive a clean, human-readable contact ID from name and email.

    Decodes MIME-encoded words, strips quotes/special chars,
    and produces a lowercase, underscore-separated identifier.
    """
    decoded = decode_rfc2047(name) if name else ""
    if not decoded:
        decoded = email.split("@")[0]
    # Replace non-word chars with underscore, collapse, strip
    normalized = re.sub(r"[^\w]+", "_", decoded).strip("_").lower()
    normalized = re.sub(r"_+", "_", normalized)
    return normalized or email.split("@")[0].lower()


def _rebuild_contacts(path: Path) -> None:
    click.echo("Scanning mailbox for contacts...", err=True)
    counter: dict[tuple[str, str], int] = {}
    cfg = get_config()
    profiles = cfg.profiles if cfg.profiles else [""]
    for prof in profiles:
        for subdir in ("incoming", "archive", "sent"):
            path_key = f"{prof}/{subdir}" if prof else subdir
            msgs = maildir_list_all(path_key)
            click.echo(f"  {path_key}: {len(msgs)} messages", err=True)
            for msg in msgs:
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
                            clean_id = _normalize_id(name, email)
                            key = (clean_id, email.lower())
                            counter[key] = counter.get(key, 0) + 1
    with open(path, "w") as f:
        for (name, email), count in sorted(counter.items(), key=lambda x: -x[1]):
            f.write(f"{name}\t{email}\t{count}\n")


def _contacts_interactive(entries: list[tuple[str, str, int]]) -> None:
    """Pipe contacts through fzf for interactive browsing.

    Falls back to non-interactive TSV output if fzf not available.
    """
    if not entries:
        return

    if not shutil.which("fzf"):
        click.echo("fzf not found. Install fzf for interactive mode.", err=True)
        for name, email, count in entries:
            click.echo(f"{name:40}\t{email:40s}\t{count:2d}")
        return

    try:
        tty_fd = os.open("/dev/tty", os.O_RDONLY)
    except OSError:
        click.echo("interactive mode requires a terminal", err=True)
        raise SystemExit(1) from None

    # Format: name<TAB>email — one per line
    fzf_input = "\n".join(f"{name}\t{email}" for name, email, _count in entries)

    try:
        proc = subprocess.run(
            [
                "fzf",
                "--multi",
                "--delimiter",
                "\t",
                "--with-nth=1",
                "--preview",
                "echo {2}",
                "--preview-window",
                "bottom:1",
                "--header",
                "Tab to select, Enter to confirm",
            ],
            input=fzf_input,
            stdin=tty_fd,
            stdout=subprocess.PIPE,
            text=True,
        )
    finally:
        os.close(tty_fd)

    if proc.returncode == 0:
        for line in proc.stdout.strip().splitlines():
            if line:
                parts = line.split("\t")
                name = parts[0]
                email = parts[1] if len(parts) > 1 else ""
                click.echo(f"{name:40}\t{email:40s}")


def _read_contacts(path: Path) -> list[tuple[str, str, int]]:
    result: list[tuple[str, str, int]] = []
    for line in path.read_text().strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            result.append((parts[0], parts[1], int(parts[2])))
    return result
