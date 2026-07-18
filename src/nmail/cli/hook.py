"""nmail hook — manually trigger a hook event."""

from __future__ import annotations

import click

from ..logging import log_event


@click.command()
@click.argument("event")
@click.argument("args", nargs=-1)
def hook(event: str, args: tuple[str, ...]) -> None:
    """Manually trigger a hook event.

    Fires matching scripts in ~/.config/nmail/hooks.d/.
    Prefixed with 'mail:' if not already.

    Examples:

    nmail hook new 3
    nmail hook sent queue-abc123
    nmail hook error queue-abc123 "SMTP timeout"
    """
    if not event.startswith("mail:"):
        event = f"mail:{event}"
    log_event(event, *args)
