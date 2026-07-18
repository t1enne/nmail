"""nmail — terminal-first mail client."""

from pathlib import Path
from typing import Final

# ── Paths ────────────────────────────────────────────────────────────────────
XDG_CONFIG_HOME: Final = Path.home() / ".config"
XDG_DATA_HOME: Final = Path.home() / ".local" / "share"
XDG_STATE_HOME: Final = Path.home() / ".local" / "state"

NM_CONFIG_HOME: Final = Path(
    Path.home() / ".config" / "nmail"
)  # fallback; overridden by NM_CONFIG_HOME env
NM_MAILDIR: Final = Path.home() / "Mail"

# ── Maildir structure ────────────────────────────────────────────────────────
INCOMING: str = "incoming"
ARCHIVE: str = "archive"
SENT: str = "sent"
DRAFTS: str = "drafts"
QUEUE: str = "queue"
TRASH: str = "trash"

MAILDIR_SUBDIRS: Final = (INCOMING, ARCHIVE, SENT, DRAFTS, QUEUE, TRASH)
MAILDIR_SUBFOLDERS: Final = ("new", "cur", "tmp")

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_TEMPLATE: Final = "default"
DEFAULT_PAGER: Final = "less"
DEFAULT_SMTP_CMD: Final = "msmtp -t"
DEFAULT_SYNC_TOOL: Final = "mbsync"
DEFAULT_SYNC_INTERVAL: Final = 300
