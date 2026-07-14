# nmail — Unix-style terminal mail environment

> **Status:** Design complete. Phase 0 (MVP) implemented.
> tmux is the orchestrator, not the mail client.

## Philosophy

nmail treats email as data (Maildir + Markdown), not as a GUI object.
Every tool is a standalone Unix command. Compose with pipes. Tmux provides
the workspace—nothing more.

```
mail-search tag:unread | fzf | xargs mail-open
mail-search tag:todo | mail-archive -
mail-contacts alice | fzf | xargs mail-compose --to
```

## Quick Start

```bash
# Install
./install.sh

# Ensure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Configure msmtp for SMTP
$EDITOR ~/.msmtprc

# Configure mbsync for IMAP
$EDITOR ~/.mbsyncrc

# Sync mail
mail-sync

# Launch workspace
mail-session
```

## Commands

| Command | Description |
|---|---|
| `mail-compose` | Create/edit draft, validate, queue |
| `mail-render` | Markdown → RFC5322 MIME |
| `mail-send` | Drain queue → SMTP (msmtp) |
| `mail-sync` | Sync with IMAP (mbsync) |
| `mail-watch` | Watch Maildir, fire events |
| `mail-open` | Open message in pager |
| `mail-reply` | Create reply draft |
| `mail-forward` | Create forward draft |
| `mail-search` | Search mail (notmuch or rg fallback) |
| `mail-tag` | Add/remove notmuch tags |
| `mail-archive` | Move to archive |
| `mail-trash` | Move to trash / empty trash |
| `mail-contacts` | Extract/query contacts |
| `mail-template` | Manage draft templates |
| `mail-status` | Mailbox statistics |
| `mail-log` | Query activity log |
| `mail-attach` | Manage attachments |
| `mail-hook` | Trigger hook scripts |
| `mail-session` | Launch tmux workspace |

## Architecture

```
                    mail-session (tmux bootstrap)
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ compose  │    │ inbox    │    │ search   │
    │ (nvim)   │    │ (lf)     │    │ (fzf)    │
    └──────────┘    └──────────┘    └──────────┘
          │                │                │
          ▼                ▼                ▼
    ┌────────────────────────────────────────────┐
    │         STANDALONE UNIX COMMANDS           │
    │   mail-compose, mail-render, mail-send,    │
    │   mail-sync, mail-search, mail-open, ...   │
    └────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
    ┌────────────────────────────────────────────┐
    │              FILESYSTEM                    │
    │              ~/Mail/                       │
    │   incoming/ archive/ drafts/ sent/         │
    │   trash/ queue/ attachments/ logs/         │
    └────────────────────────────────────────────┘
```

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

~/.local/bin/
├── mail-compose         # and all other commands

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

## Dependencies

**Required:** bash, coreutils, tmux
**Recommended:** msmtp (SMTP), mbsync (IMAP), notmuch (search), pandoc (HTML), nvim (editor), lf (file browser), fzf (picker), bat (pager), jq (JSON)
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
- [ ] Phase 1: sync, search, reply, forward, tag, archive, trash, contacts, watch
- [ ] Phase 2: tmux session, hooks
- [ ] Phase 3: templates, attachments, plugins
- [ ] Phase 4: community extensions

## License

MIT
