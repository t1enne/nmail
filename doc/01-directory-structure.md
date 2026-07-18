# nmail Directory Structure

```
~/.config/nmail/
├── config.toml              # Main configuration
├── hooks.d/                 # Event hooks (executables)
│   ├── on-new               # New mail arrived
│   ├── on-sent              # Message sent
│   ├── on-error             # Send failure
│   ├── on-sync-start        # Sync began
│   └── on-sync-end          # Sync completed
└── accounts/                # Per-account overrides
    ├── personal.toml
    └── work.toml

~/Mail/                      # Maildir root
├── incoming/                # Incoming (Maildir)
│   ├── cur/                 # Read messages
│   ├── new/                 # Unread messages
│   └── tmp/                 # Delivery in progress
├── archive/                 # Archived (Maildir++)
│   └── cur/
├── drafts/                  # Markdown drafts
│   └── *.md
├── sent/                    # Sent (Maildir)
│   ├── cur/
│   ├── new/
│   └── tmp/
├── trash/                   # Trash (Maildir)
│   ├── cur/
│   ├── new/
│   └── tmp/
├── attachments/             # Saved attachments
├── queue/                   # Outbound queue (Maildir)
│   ├── new/                 # Pending send
│   ├── cur/                 # Sent / failed
│   └── tmp/                 # In progress
├── templates/               # Draft templates
│   ├── default.md
│   ├── reply.md
│   └── forward.md
└── logs/                    # Log files
    ├── mail.log             # Structured activity log
    ├── sync.log             # mbsync output
    └── send.log             # msmtp output

~/Mail/.notmuch/             # notmuch database (optional)
│   └── xapian/

~/.local/state/nmail/        # Runtime state
├── last-sync                # Timestamp of last sync
├── queue-lock               # Queue processing lock
└── contacts.tsv             # Cached contact list
```

## Project Repository (this dir)

```
nmail/
├── src/nmail/                # Python package
│   ├── __init__.py
│   ├── cli.py                # Click entrypoint (all subcommands)
│   ├── cli_commands1.py
│   ├── cli_commands2.py
│   ├── config.py             # TOML config loader
│   ├── constants.py
│   ├── drafts.py             # Draft parsing (MD + headers)
│   ├── headers.py            # Header extraction
│   ├── logging.py            # Structured log
│   ├── maildir.py            # Maildir operations
│   ├── notmuch.py            # notmuch wrapper
│   ├── render.py             # Markdown → RFC5322 MIME
│   └── shared.py             # Shared helpers
├── config/
│   ├── config.toml           # Default configuration
│   └── hooks.d/              # Example hooks
│       ├── on-new
│       ├── on-sent
│       └── on-error
├── templates/
│   ├── default.md
│   ├── reply.md
│   └── forward.md
├── doc/
│   ├── 00-architecture.md
│   ├── 01-directory-structure.md
│   ├── 02-process-flows.md
│   ├── 03-cli-spec.md
│   ├── 04-configuration.md
│   ├── 05-tmux-session.md
│   ├── 06-composability.md
│   ├── 07-hooks.md
│   ├── 08-implementation-plan.md
│   ├── 09-example-pipelines.md
│   └── 10-installation-and-e2e-guide.md
├── pyproject.toml            # Python project config + deps
├── Makefile                  # format, lint, typecheck
└── README.md
```
