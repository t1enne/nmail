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

~/.local/bin/                # All commands (in PATH)
├── mail-session             # tmux bootstrap
├── mail-compose             # Open draft in $EDITOR
├── mail-render              # Markdown → MIME
├── mail-send                # Drain queue → SMTP
├── mail-sync                # Fetch via mbsync/offlineimap
├── mail-watch               # inotifywait on Maildir
├── mail-open                # Open message by ID
├── mail-reply               # Reply to message
├── mail-forward             # Forward message
├── mail-search              # notmuch/fzf/grep search
├── mail-tag                 # Add/remove notmuch tags
├── mail-archive             # Move to archive/
├── mail-trash               # Move to trash/
├── mail-contacts            # Extract/query contacts
├── mail-template            # Manage draft templates
├── mail-status              # Counts, queue state
├── mail-log                 # Query structured log
├── mail-attach              # Manage attachment dir
└── mail-hook                # Run hooks.d/ scripts

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
├── bin/                      # Executable scripts (linked to ~/.local/bin/)
│   ├── mail-session
│   ├── mail-compose
│   ├── mail-render
│   ├── mail-send
│   ├── mail-sync
│   ├── mail-watch
│   ├── mail-open
│   ├── mail-reply
│   ├── mail-forward
│   ├── mail-search
│   ├── mail-tag
│   ├── mail-archive
│   ├── mail-trash
│   ├── mail-contacts
│   ├── mail-template
│   ├── mail-status
│   ├── mail-log
│   ├── mail-attach
│   └── mail-hook
├── src/                      # Shared libraries (bash)
│   ├── common.sh             # Logging, Maildir helpers, config parsing
│   ├── render.sh             # Markdown → MIME pipeline
│   ├── maildir.sh            # Maildir operations
│   └── notmuch.sh            # notmuch wrapper (graceful fallback)
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
│   └── 09-example-pipelines.md
├── install.sh                # Symlink bin/ → ~/.local/bin/, init ~/Mail/
├── Makefile                  # install, uninstall, test
└── README.md
```
