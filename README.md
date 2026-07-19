# nmail — terminal-first mail client

## Philosophy

nmail treats email as data (Maildir + Markdown), not as a GUI object.
Compose with pipes. Every subcommand is a standalone action.

```bash
# Browse unread with fzf preview, then act on selections
nmail search --interactive tag:unread | while read id; do nmail open "$id"; done
nmail search --interactive tag:todo   | while read id; do nmail reply "$id"; done

# Batch operations via pipes (use --format ids for machine-readable IDs)
nmail search --format ids tag:unread --quiet | nmail tag -- -unread -  # Mark all unread as read
nmail search --format ids tag:todo | nmail archive -
nmail search --format ids from:bob | nmail tag +bob -

# Contacts to compose
nmail contacts alice | awk '{print $2}' | head -1 | xargs nmail compose --to
```

## Quick Start

```bash
# Install
uv tool install .

# Or for development
uv run nmail --help

# Configure msmtp for SMTP
$EDITOR ~/.msmtprc

# Configure mbsync for IMAP
$EDITOR ~/.mbsyncrc

# Edit nmail config (optional — defaults work)
$EDITOR ~/.config/nmail/config.toml

# Sync mail
nmail sync

# Compose a draft
nmail compose

# Send queued mail
nmail send
```

### Composing Pipelines

```bash
# Daily inbox triage: tag, archive, trash in one pass
nmail search --format ids tag:unread --quiet | nmail tag -- -unread -  # Mark all as read
nmail search --format ids tag:unread from:alice | nmail tag +important -
nmail search --format ids tag:unread subject:'newsletter' | nmail archive -
nmail search --format ids subject:'spam' | nmail trash -

# Reply to all flagged messages
nmail search --format ids tag:flagged | while read id; do nmail reply "$id"; done

# Check for send failures and retry
nmail log --since 1h --level error | grep -q mail:error && nmail send --all

# Daily digest (script)
nmail search --format summary tag:unread --limit 20
nmail status
```

## Commands

| Command          | Description                       |
| ---------------- | --------------------------------- |
| `nmail compose`  | Create/edit draft                 |
| `nmail render`   | Markdown → RFC5322 MIME           |
| `nmail send`     | Send queued mail via msmtp        |
| `nmail sync`     | Sync Maildir via mbsync           |
| `nmail watch`    | Watch Maildir, fire events        |
| `nmail open`     | Open message in pager             |
| `nmail reply`    | Create reply draft                |
| `nmail forward`  | Create forward draft              |
| `nmail search`   | Search mail (notmuch or ripgrep)  |
| `nmail tag`      | Add/remove notmuch tags           |
| `nmail archive`  | Move to archive                   |
| `nmail trash`    | Move to trash / empty trash       |
| `nmail contacts` | Extract/query contacts            |
| `nmail template` | Manage draft templates            |
| `nmail status`   | Mailbox statistics                |
| `nmail log`      | Query activity log                |
| `nmail attach`   | Manage saved attachments          |
| `nmail hook`     | Trigger hook scripts              |

## Search Syntax

nmail passes queries to notmuch. Supported prefixes:

`from:` `to:` `subject:` `tag:` `folder:` `path:` `id:` `thread:` `attachment:` `mimetype:`

```bash
# Search by folder (maildir subdirectory)
nmail search folder:spam
nmail search 'folder:"[Gmail]/Spam"'   # Gmail labels with paths
nmail search --interactive folder:inbox tag:unread

# Compound queries
nmail search 'from:bob AND subject:invoice'
nmail search 'tag:unread AND NOT folder:trash'

# Interactive browse
nmail search --interactive
nmail search --interactive tag:todo
```

### Gmail Spam

Gmail's `[Gmail]/Spam` folder is not synced by default. To include it:

1. Add to mbsync `Patterns` in `~/.mbsyncrc`:

   ```
   Patterns "INBOX" "[Gmail]/Sent Mail" "[Gmail]/Drafts" "[Gmail]/Trash" "[Gmail]/Archive" "[Gmail]/Spam"
   ```

2. Sync and re-index:

   ```bash
   nmail sync
   notmuch new
   ```

3. Search spam:

   ```bash
   nmail search 'folder:"[Gmail]/Spam"'
   nmail search --format ids 'folder:"[Gmail]/Spam" tag:unread' | nmail trash -
   ```

> **Note:** Syncing spam locally pulls every message Gmail flags as spam. If your account gets heavy spam, this can mean hundreds of unread messages. Consider whether you need local spam access or if occasional web checks suffice.

## Draft Format

```markdown
From: john@example.com
To: alice@example.com
Cc:
Subject: Meeting notes

---

Hello Alice,

Here are the notes from today:

- Item 1
- Item 2
- **Important** point

Thanks,
John
```

## Directory Structure

```
~/.config/nmail/
├── config.toml          # Main configuration
└── hooks.d/             # Event hook scripts (on-new, on-sent, on-error, etc.)

~/Mail/
├── incoming/{cur,new,tmp}/
├── archive/cur/
├── drafts/*.md
├── sent/{cur,new,tmp}/
├── trash/{cur,new,tmp}/
├── queue/{cur,new,tmp}/
├── templates/*.md
├── attachments/
└── logs/
    └── nmail.log        # JSON-line event log
```

## Configuration

```toml
# ~/.config/nmail/config.toml

# Flat top-level keys (no [general] section)
maildir = "~/Mail"
pager = "bat --plain --language=email"

[user]
from = "John Doe <john@example.com>"

[smtp]
command = "msmtp"

[sync]
tool = "mbsync"
accounts = ["personal"]
interval = 300

[notmuch]
enabled = true
command = "notmuch"

[templates]
dir = "~/Mail/templates"
default = "default"

[hooks]
enabled = true
dir = "~/.config/nmail/hooks.d"

[logging]
dir = "~/Mail/logs"
level = "info"

[notifications]
enabled = true
events = ["mail:new", "mail:error"]
```

Editor is read from `$EDITOR` or `$VISUAL` env vars (not config).
Key env overrides: `NM_MAILDIR`, `NM_PAGER`, `NM_FROM`, `NM_SMTP_CMD`, `NM_CONFIG_HOME`.

## Development

```bash
# Install dev deps
uv sync

# Format, lint, typecheck
make check

# Run
uv run nmail --help
```

## Dependencies

**Required:** Python ≥3.11, click≥8.1, tomli≥2.0
**Recommended:** msmtp (SMTP), mbsync (IMAP), notmuch (search/index), bat (pager), fzf (interactive browse)
**Optional:** ripgrep (search fallback when notmuch unavailable), inotify-tools (watch), notify-send (notifications)

## Documentation

- `doc/00-architecture.md` — Architecture overview and data flows
- `doc/01-directory-structure.md` — Full directory layout
- `doc/02-process-flows.md` — Compose→Send, Sync→Search flows
- `doc/03-cli-spec.md` — Complete CLI specification
- `doc/04-configuration.md` — Configuration format and hooks
- `doc/05-composability.md` — Composability patterns
- `doc/06-hooks.md` — Plugin and hook architecture
- `doc/07-implementation-plan.md` — Staged plan
- `doc/08-example-pipelines.md` — Shell pipeline examples
- `doc/09-installation-and-e2e-guide.md` — End-to-end setup guide

## Implementation Status

- [x] Phase 0: compose, render, send, open, status, log
- [x] Phase 1: sync, search, reply, forward, tag, archive, trash, contacts, watch
- [x] Phase 2: hooks
- [x] Phase 3: templates, attachments
- [ ] Phase 4: MIME attachment encoding in render, markdown→HTML rendering, plugins

## License

MIT
