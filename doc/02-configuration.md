# Configuration

## Format: TOML

File: `~/.config/nmail/config.toml`

```toml
# =============================================================================
# nmail configuration
# =============================================================================

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

[general]
# Maildir root. Default: ~/Mail
maildir = "~/Mail"

# Editor for composing drafts. Default: $EDITOR or nvim
editor = "nvim"

# Pager for reading mail. Default: $PAGER or less
pager = "bat --plain --language=email"

# File browser for inbox/directories. Default: lf
file_browser = "lf"

# Default signature appended to drafts
signature = """
--
John Doe
john@example.com
"""

# Default "From:" address
from_address = "John Doe <john@example.com>"

# Default template for new drafts
default_template = "default"

# ---------------------------------------------------------------------------
# Profiles (multi-account)
# ---------------------------------------------------------------------------

# Each profile gets its own subdirectory under maildir:
#   ~/Mail/personal/incoming/, ~/Mail/personal/sent/, ...
#   ~/Mail/work/incoming/,     ~/Mail/work/sent/, ...

[profiles]
# Default profile used when NM_PROFILE env is not set.
# Empty string = flat mode (legacy, no subdir).
default = "personal"

[profiles.personal]
sync_account = "personal"
smtp_account = "personal"

[profiles.work]
sync_account = "work"
smtp_account = "work"

# ---------------------------------------------------------------------------
# SMTP (sending)
# ---------------------------------------------------------------------------

[smtp]
# SMTP send command. Uses msmtp by default.
# The rendered message is piped to this command's stdin.
command = "msmtp"

# Queue processing
[queue]
# How often to drain the queue (seconds). 0 = manual only.
process_interval = 60

# Max retries for failed sends
max_retries = 3

# Retry delay between attempts (seconds)
retry_delay = 300

# ---------------------------------------------------------------------------
# IMAP (sync)
# ---------------------------------------------------------------------------

[sync]
# Sync tool: "mbsync", "offlineimap", or custom command
tool = "mbsync"

# Accounts to sync
accounts = ["personal", "work"]

# Sync interval (seconds). 0 = manual only.
interval = 300

# ---------------------------------------------------------------------------
# Indexing (notmuch)
# ---------------------------------------------------------------------------

[notmuch]
# Enable notmuch integration
enabled = true

# notmuch binary path
command = "notmuch"

# Extra arguments for notmuch new
new_args = ""

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

[hooks]
# Directory containing hook scripts
dir = "~/.config/nmail/hooks.d/"

# Enable hook execution
enabled = true

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

[logging]
# Log directory
dir = "~/Mail/logs"

# Log level: debug, info, warn, error
level = "info"

# Maximum log file size before rotation (MB)
max_size = 10

# Keep this many rotated logs
keep = 5

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

[notifications]
# Enable desktop notifications (via notify-send)
enabled = true

# Only notify for these events (empty = all)
events = ["mail:new", "mail:error"]

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

[templates]
# Directory for draft templates
dir = "~/Mail/templates"

# Default template to use
default = "default"
```

## Environment Variables

All config values can be overridden via environment:

| Variable | Config key |
|---|---|
| `MAIL_DIR` | `general.maildir` |
| `MAIL_EDITOR` | `general.editor` |
| `MAIL_PAGER` | `general.pager` |
| `MAIL_FILE_BROWSER` | `general.file_browser` |
| `MAIL_FROM` | `general.from_address` |
| `MAIL_SIGNATURE` | `general.signature` |
| `MAIL_SMTP_CMD` | `smtp.command` |
| `MAIL_SYNC_TOOL` | `sync.tool` |
| `MAIL_SYNC_INTERVAL` | `sync.interval` |
| `MAIL_TMPL_DIR` | `templates.dir` |
| `NM_PROFILE` | Active profile name (overrides config default) |
| `NM_DRY_RUN` | (all commands: dry-run mode) |
| `NM_VERBOSE` | (all commands: verbose output) |

## Account Configuration (msmtp example)

`~/.msmtprc`:

```
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        ~/Mail/logs/send.log

account personal
host           smtp.example.com
port           587
from           john@example.com
user           john@example.com
passwordeval   pass show mail/personal

account work
host           smtp.company.com
port           587
from           john@company.com
user           john@company.com
passwordeval   pass show mail/work

account default : personal
```

## Sync Configuration (mbsync example)

### Single profile

`~/.mbsyncrc`:

```
IMAPAccount personal
Host imap.example.com
User john@example.com
PassCmd "pass show mail/personal"
SSLType IMAPS

IMAPStore personal-remote
Account personal

MaildirStore personal-local
Path ~/Mail/
Inbox ~/Mail/inbox
SubFolders Verbatim

Channel personal
Far :personal-remote:
Near :personal-local:
Patterns "INBOX" "[Gmail]/Sent Mail" "[Gmail]/Drafts" "[Gmail]/Trash"
Create Both
Expunge Both
SyncState *
```

### Multiple profiles

Each profile gets its own subdirectory under `~/Mail/`:

```
IMAPAccount personal
Host imap.gmail.com
User john@gmail.com
PassCmd "pass show mail/personal"
SSLType IMAPS

IMAPStore personal-remote
Account personal

MaildirStore personal-local
Path ~/Mail/personal/
Inbox ~/Mail/personal/incoming
SubFolders Verbatim

Channel personal
Far :personal-remote:
Near :personal-local:
Patterns "INBOX" "[Gmail]/Sent Mail" "[Gmail]/Drafts" "[Gmail]/Trash"
Create Both
Expunge Both
SyncState *

IMAPAccount work
Host outlook.office365.com
User john@company.com
PassCmd "pass show mail/work"
SSLType IMAPS

IMAPStore work-remote
Account work

MaildirStore work-local
Path ~/Mail/work/
Inbox ~/Mail/work/incoming
SubFolders Verbatim

Channel work
Far :work-remote:
Near :work-local:
Patterns "INBOX" "Sent Items" "Drafts" "Trash"
Create Both
Expunge Both
SyncState *
```

## Hooks Directory

`~/.config/nmail/hooks.d/` — each file is an executable script.

```
on-new          # Called when new mail arrives
on-sent         # Called when message sent
on-error        # Called when send fails
on-sync-start   # Called when sync starts
on-sync-end     # Called when sync ends
on-draft        # Called when draft saved
on-trash        # Called when message moved to trash
on-archive      # Called when message archived
```

### Hook Contract

Each hook receives:
- `$1` = event name (e.g., `mail:new`)
- `$2+` = event-specific arguments

**on-new example:**

```bash
#!/bin/bash
count="$2"
notify-send "Mail" "$count new message(s)" --icon=mail-unread
```

**on-sent example:**

```bash
#!/bin/bash
id="$2"
echo "Sent: $id" >> ~/.mail-sent.log
```

**on-error example:**

```bash
#!/bin/bash
id="$2"
error="$3"
notify-send -u critical "Mail Error" "Failed to send $id: $error"
```

## Plugin Architecture

Plugins are hook scripts with dependencies. A plugin is a directory:

```
~/.config/nmail/plugins/<name>/
├── plugin.toml       # Metadata
├── hooks.d/          # Hook scripts (symlinked or copied)
└── scripts/          # Helper scripts
```

`plugin.toml`:

```toml
[plugin]
name = "notify-desktop"
version = "1.0.0"
description = "Desktop notifications via notify-send"

[hooks]
"mail:new" = "hooks.d/on-new"
"mail:error" = "hooks.d/on-error"

[requirements]
commands = ["notify-send"]
```
