"""nmail CLI — terminal-first mail client."""

from __future__ import annotations

import click

from .cli_commands1 import (
    compose,
    forward,
    open_cmd,
    render_cmd,
    reply,
    search,
    send,
    status,
    sync,
)
from .cli_commands2 import (
    archive,
    attach,
    contacts,
    hook,
    log_cmd,
    session,
    tag,
    template,
    trash,
    watch,
)


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
