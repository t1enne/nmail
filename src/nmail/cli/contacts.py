"""nmail contacts — search and manage contacts."""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..headers import extract_header
from ..maildir import maildir_list_all


@click.command()
@click.option("--update", is_flag=True)
@click.option("--format", "fmt", type=click.Choice(["tsv", "json"]), default="tsv")
@click.argument("query", required=False)
def contacts(update: bool, fmt: str, query: str | None) -> None:
    """Search and manage contacts.

    Builds contact database from email headers (From, To, Cc).
    Cache at ~/.local/state/nmail/contacts.tsv.

    Examples:

    nmail contacts --update
    nmail contacts alice
    nmail contacts --format json
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
            click.echo(f"{name:40}\t{email:40s}\t{count:2d}")


def _rebuild_contacts(path: Path) -> None:
    click.echo("Scanning mailbox for contacts...", err=True)
    counter: dict[tuple[str, str], int] = {}
    for subdir in ("incoming", "archive", "sent"):
        msgs = maildir_list_all(subdir)
        click.echo(f"  {subdir}: {len(msgs)} messages", err=True)
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
