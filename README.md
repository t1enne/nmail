# nmail — terminal-first mail client

> **Status:** All 19 subcommands implemented. Compose, render, send, sync, search, reply, forward, tag, archive, trash, contacts, watch, session, hooks, templates, attachments all working.
> All commands under single `nmail` binary.

## Philosophy

nmail treats email as data (Maildir + Markdown), not as a GUI object.
Compose with pipes. Every subcommand is a standalone action.

```
nmail search --tag unread | fzf | xargs nmail open
nmail search --tag todo | nmail archive -
nmail contacts alice | fzf | xargs nmail compose --to
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

# Sync mail
nmail sync

# Compose a draft
nmail compose
```

## Commands

| Command | Description |
|---|---|
| `nmail compose` | Create/edit draft |
| `nmail render` | Markdown → RFC5322 MIME |
| `nmail send` | Send queued mail via msmtp |
| `nmail sync` | Sync Maildir via mbsync |
| `nmail watch` | Watch Maildir, fire events |
| `nmail open` | Open message in pager |
| `nmail reply` | Create reply draft |
| `nmail forward` | Create forward draft |
| `nmail search` | Search mail (notmuch) |
| `nmail tag` | Add/remove notmuch tags |
| `nmail archive` | Move to archive |
| `nmail trash` | Move to trash / empty trash |
| `nmail contacts` | Extract/query contacts |
| `nmail template` | Manage draft templates |
| `nmail status` | Mailbox statistics |
| `nmail log` | Query activity log |
| `nmail attach` | Manage attachments |
| `nmail hook` | Trigger hook scripts |
| `nmail session` | Launch tmux workspace |

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
└── hooks.d/             # Event hooks
    ├── on-new
    ├── on-sent
    └── on-error

~/Mail/
├── incoming/{cur,new,tmp}/
├── archive/cur/
├── drafts/*.md
├── sent/{cur,new,tmp}/
├── trash/{cur,new,tmp}/
├── queue/{cur,new,tmp}/
├── templates/*.md
├── attachments/
└── logs/{mail,sync,send}.log
```

## Configuration

```toml
# ~/.config/nmail/config.toml
[general]
maildir = "~/Mail"
editor = "nvim"
pager = "bat --plain --language=email"
file_browser = "lf"
from_address = "John Doe <john@example.com>"

[smtp]
command = "msmtp"

[sync]
tool = "mbsync"
accounts = ["personal"]

[notmuch]
enabled = true
```

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

**Required:** Python ≥3.11, click
**Recommended:** msmtp (SMTP), mbsync (IMAP), notmuch (search), nvim (editor), lf (file browser), fzf (picker), bat (pager)
**Optional:** ripgrep (search fallback), inotify-tools (watch), notify-send (notifications)

## Documentation

- `doc/00-architecture.md` — Architecture overview and data flows
- `doc/01-directory-structure.md` — Full directory layout
- `doc/02-process-flows.md` — Compose→Send, Sync→Search flows
- `doc/03-cli-spec.md` — Complete CLI specification
- `doc/04-configuration.md` — Configuration format and hooks
- `doc/05-tmux-session.md` — mail-session launcher
- `doc/06-composability.md` — Example shell pipelines
- `doc/07-hooks.md` — Plugin and hook architecture
- `doc/08-implementation-plan.md` — Staged plan (MVP through full)
- `doc/09-example-pipelines.md` — Usage examples

## Implementation Status

- [x] Phase 0 (MVP): compose, render, send, open, status, log
- [x] Phase 1: sync, search, reply, forward, tag, archive, trash, contacts, watch
- [x] Phase 2: tmux session, hooks
- [x] Phase 3: templates, attachments
- [ ] Phase 4: plugins, community extensions

## License

MIT
