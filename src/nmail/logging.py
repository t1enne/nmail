"""Logging and event system."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
from datetime import UTC, datetime

from .config import get_config


def _format_ts() -> str:
    return datetime.now(UTC).isoformat()


def log_event(event: str, *args: str) -> None:
    """Write structured JSON log line and fire hooks."""
    cfg = get_config()
    log_dir = cfg.logging_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "nmail.log"

    entry = {
        "ts": _format_ts(),
        "event": event,
        "args": list(args),
    }
    with open(log_file, "a") as f:
        json.dump(entry, f)
        f.write("\n")

    # Fire hooks
    hooks_dir = cfg.hooks_dir
    if hooks_dir and hooks_dir.exists():
        hook_name = event.removeprefix("mail:")
        for hook in sorted(hooks_dir.glob(f"on-{hook_name}*")):
            if hook.is_file() and os.access(hook, os.X_OK):
                with contextlib.suppress(Exception):
                    subprocess.run(
                        [str(hook), event, *args],
                        timeout=30,
                    )


def log_info(msg: str) -> None:
    log_event("info", msg)


def log_warn(msg: str) -> None:
    log_event("warn", msg)


def log_error(msg: str) -> None:
    log_event("error", msg)
