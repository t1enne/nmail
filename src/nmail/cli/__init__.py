"""nmail CLI — terminal-first mail client."""

from __future__ import annotations

import click

from .archive import archive
from .attach import attach
from .compose import compose
from .contacts import contacts
from .forward import forward
from .hook import hook
from .log import log_cmd
from .open import open_cmd
from .render import render_cmd
from .reply import reply
from .search import search
from .send import send
from .session import session
from .status import status
from .sync import sync
from .tag import tag
from .template import template
from .trash import trash
from .watch import watch


@click.group()
def main() -> None:
    """nmail — terminal-first mail client."""


main.add_command(search, "search")
main.add_command(reply, "reply")
main.add_command(compose, "compose")
main.add_command(send, "send")
main.add_command(forward, "forward")
main.add_command(open_cmd, "open")
main.add_command(sync, "sync")
main.add_command(status, "status")
main.add_command(render_cmd, "render")
main.add_command(template, "template")
main.add_command(attach, "attach")
main.add_command(archive, "archive")
main.add_command(contacts, "contacts")
main.add_command(tag, "tag")
main.add_command(trash, "trash")
main.add_command(session, "session")
main.add_command(hook, "hook")
main.add_command(watch, "watch")
main.add_command(log_cmd, "log")
