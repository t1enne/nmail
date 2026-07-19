---
name: nmail
description: Terminal-first mail toolkit — compose, search, reply, tag, and manage email via CLI. Use when the user needs to read email, compose messages, search mail, manage tags, reply/forward, sync IMAP, check mailbox status, watch for new mail, or manage templates/attachments.
allowed-tools: Bash(nmail:*)
---

# nmail — Terminal Mail Client

nmail is a composable Unix mail toolkit that treats email as plain data, letting you search, compose, automate, and process mail with shell pipelines instead of living inside a terminal UI. Unlike monolithic clients (mutt, aerc, sup), nmail doesn't own your screen — it provides standalone subcommands that each do one thing and output to stdout. Compose with your editor on Markdown files. Send asynchronously through a queue. Search with notmuch or ripgrep. Hook into every event with shell scripts. No daemon, no database, no lock-in — just Maildir and pipes.

`nmail` is a Python CLI tool that treats email as data (Maildir + Markdown). Every subcommand is a standalone action — composable with pipes, fzf, and shell pipelines.

## Documentation

Detailed usage docs in the repo:

- `doc/01-cli-spec.md` — Every subcommand, flag, output format
- `doc/02-configuration.md` — TOML config, hooks, env overrides
- `doc/03-composability.md` — Pipe philosophy and patterns
- `doc/04-example-pipelines.md` — Concrete pipeline recipes
- `doc/05-installation-and-e2e-guide.md` — Install + guided walkthrough

## Requirements

nmail must be installed before use. See the [install guide](https://github.com/nasrt/nmail/blob/main/INSTALL.md) and [configuration guide](https://github.com/nasrt/nmail/blob/main/CONFIG.md) in the GitHub repo.

In short:

- **System deps:** msmtp (SMTP), mbsync (IMAP), Python ≥3.11. Recommended: notmuch, bat, fzf.
- **Install:** `uv tool install git+https://github.com/nasrt/nmail`
- **Configure:** `~/.msmtprc` (SMTP), `~/.mbsyncrc` (IMAP), `~/.config/nmail/config.toml` (optional)

## Quick Reference

```bash
nmail --help                          # List all subcommands
nmail sync                            # Fetch mail via mbsync
nmail search --interactive            # Browse mail with fzf preview
nmail compose --to alice@example.com  # Compose new message
nmail reply 182                       # Reply to message ID 182
nmail send                            # Send next queued message
nmail open 182                        # Open message in pager
nmail status                          # Mailbox statistics
nmail tag -- +todo 182                # Add "todo" tag
nmail archive 182                     # Archive message
nmail trash 182                       # Trash message
nmail contacts alice                  # Search contacts
nmail watch                           # Watch for new mail
nmail log --since 1h                  # Recent activity
nmail hook new 3                      # Fire on-new hook for 3 messages
```

## Commands

### Compose

Create/edit a Markdown draft. On save, validates and queues for sending.

```bash
nmail compose                                    # Open editor with default template
nmail compose --to alice@example.com             # Pre-fill To header
nmail compose --to alice --subject "Meeting"     # Pre-fill multiple headers
nmail compose --no-send                          # Save draft, don't queue
nmail compose --attach file.pdf                  # Attach files to draft
echo -e "To: a@b\nSubject: hi\n---\n\nHello" | nmail compose --stdin  # From stdin
```

**Draft format** (Markdown with RFC822-style headers above `---` separator):

```
From: john@example.com
To: alice@example.com
Cc:
Subject: Meeting notes

---

Hello Alice,

Here are the notes.

Thanks,
John
```

Header block above `---`, Markdown body below. Optional second `---` block for attachment list.

### Send

Drain queue/new/ through msmtp. Success → sent/, failure → queue/cur/.

```bash
nmail send                           # Send next queued message
nmail send --all                     # Send all queued messages
nmail send --dry-run                 # Preview what would be sent
nmail send --retry 3                 # Retry up to 3 times on failure
nmail send --id queue-abc123         # Send specific message
```

Requires msmtp configured at `~/.msmtprc`.

### Sync

Fetch mail via mbsync, optionally re-index with notmuch.

```bash
nmail sync                           # Sync all configured accounts
nmail sync --account work            # Sync specific account
nmail sync --dry-run                 # Preview command
nmail sync --no-index                # Skip notmuch re-index
```

### Search

Full-text search via notmuch (recommended), fallback to ripgrep/grep.

```bash
nmail search                         # Default: list all messages (summary format)
nmail search tag:unread              # Notmuch query syntax
nmail search from:alice subject:invoice
nmail search 'tag:unread from:alice' # Compound queries
nmail search --interactive           # Browse results with fzf + preview
nmail search --format ids tag:todo   # Output message IDs for piping
nmail search --format json from:bob  # JSON output
nmail search --format summary tag:unread  # One-line-per-message table
nmail search --format preview tag:unread  # Rendered previews
nmail search --limit 20 from:bob
```

**Output formats:** `summary` (default, date/from/subject table), `ids` (message IDs), `files` (full paths), `json`, `preview` (full rendered markdown-style)

**Pipe pattern:**

```bash
nmail search --format ids tag:unread | while read id; do nmail open "$id"; done
nmail search --format ids tag:todo | nmail archive -
nmail search --format ids tag:unread | nmail tag -- +read -

# Interactive selection → act on chosen messages
nmail search --interactive tag:unread | while read id; do nmail open "$id"; done
nmail search --interactive tag:todo   | while read id; do nmail reply "$id"; done
```

### Open

Open message in pager (bat if available, otherwise configured pager).

```bash
nmail open 182                       # Open by message ID
nmail open ~/Mail/incoming/new/...   # Open by file path
nmail open --raw 182                 # Show raw RFC5322 message
```

Marks message as read (moves `new/` → `cur/`, adds `S` flag).

### Reply / Forward

```bash
nmail reply 182                      # Reply to sender
nmail reply --all 182                # Reply to all
nmail reply --no-quote 182           # Don't quote original
nmail reply --template quick 182     # Use custom template
nmail forward 182                    # Forward with quoted block
nmail forward --template simple 182
```

Both validate on save → queue for sending.

### Tag

Add/remove notmuch tags. Requires notmuch.

```bash
nmail tag -- +todo 182                  # Add tag (must start with +)
nmail tag -- -unread 182                # Remove tag (must start with -)
nmail tag -- +work 182 193 204          # Tag multiple messages
nmail search --format ids from:bob | nmail tag -- +bob -   # Tag from pipe
```

### Archive / Trash

```bash
# Archive: moves from incoming/ → archive/cur/
nmail archive 182 193
nmail search --format ids tag:todo | nmail archive -

# Trash: moves to trash/
nmail trash 182 193
nmail trash --empty                  # Empty entire trash
nmail trash --empty --force          # Skip confirmation
nmail trash --age 30                 # Purge trash older than 30 days
nmail search --format ids subject:spam | nmail trash -
```

### Status

Mailbox statistics.

```bash
nmail status                         # Human-readable table
nmail status --json                  # JSON output
nmail status --watch                 # Refresh every 10s
```

### Contacts

Build and query contact database from email headers.

```bash
nmail contacts --update              # Rebuild contact cache
nmail contacts alice                 # Search contacts matching "alice"
nmail contacts --format json         # JSON output
```

Cache at `~/.local/state/nmail/contacts.tsv`.

### Watch

Monitor Maildir for new mail.

```bash
nmail watch                          # Watch incoming/new/ (persistent)
nmail watch --once                   # One-shot count of new messages
nmail watch --no-hooks               # Don't fire hook scripts
```

Uses inotifywait if available, otherwise polls every 5s.

### Template

Manage draft templates in `~/Mail/templates/`. Built-in: `default`, `reply`, `forward`.

```bash
nmail template list                  # List available templates
nmail template show default          # Show template content
nmail template create meeting        # Create new template (opens editor)
nmail template edit reply            # Edit existing template
nmail template delete obsolete       # Delete template
cat template.md | nmail template create my-template  # From stdin
```

### Attach

Manage saved attachments in `~/Mail/attachments/`. Attachments are saved to this directory during compose with `--attach`, then available for listing, opening, or copying out.

```bash
nmail attach list                    # List saved attachments
nmail attach save *.pdf              # Copy attachments to current dir
nmail attach open invoice.pdf        # Open attachment with system handler
nmail attach clean                   # Delete all saved attachments
```

### Hook

Manually trigger hook event. Fires matching scripts in `~/.config/nmail/hooks.d/`.

```bash
nmail hook new 3                     # Fire on-new hook
nmail hook sent queue-abc123         # Fire on-sent hook
nmail hook error queue-abc123 "SMTP timeout"
```

Event gets `mail:` prefix if not already present.

### Log

View structured JSON event log.

```bash
nmail log                            # Show all log entries
nmail log --follow                   # Tail the log
nmail log --event mail:send          # Filter by event type
nmail log --level error              # Filter by level
nmail log --since 2026-07-13         # Filter by date
nmail log --since 1h --level error   # Combine filters
nmail log --json | jq                # JSON output
```

### Render

Render Markdown draft to RFC5322 MIME format. Useful for debugging.

```bash
nmail render draft.md                # Render to MIME (multipart/alternative)
nmail render --format plain draft.md # Text/plain only
nmail render --format html draft.md  # Text/html only
nmail render queue/new/msg123        # Render queued message
```

## Directory Structure

```
~/.config/nmail/
├── config.toml          # Main configuration
└── hooks.d/             # Event hook scripts (on-new, on-sent, on-error, etc.)

~/Mail/
├── incoming/{cur,new,tmp}/   # Inbox
├── archive/cur/              # Archived messages
├── drafts/*.md               # Drafts (Markdown)
├── sent/{cur,new,tmp}/       # Sent mail
├── trash/{cur,new,tmp}/      # Trash
├── queue/{cur,new,tmp}/      # Outgoing queue
├── templates/*.md            # Draft templates
├── attachments/              # Saved attachments
└── logs/
    └── nmail.log             # JSON-line event log
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

## Dependencies

| Category        | Tools                                                                                                |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| **Required**    | Python ≥3.11, click≥8.1, tomli≥2.0, msmtp (or other SMTP command), mbsync (or other IMAP sync tool)  |
| **Recommended** | notmuch (tagging, fast search, unread counts), bat (pager), fzf (interactive browse)                 |
| **Optional**    | ripgrep (better grep fallback), inotify-tools (efficient watch), notify-send (desktop notifications) |

msmtp and mbsync are practically mandatory — without SMTP you can't send, without IMAP sync you can't receive. The binary names are configurable (`smtp.command`, `sync.tool`) but the function isn't optional.

## Composing Commands (Pipes & Patterns)

nmail is built for composition. Every subcommand outputs plain text — pipe, filter, chain.

```bash
# Interactive browse → open or reply to selections (fzf multi-select)
nmail search --interactive tag:unread | while read id; do nmail open "$id"; done
nmail search --interactive tag:todo   | while read id; do nmail reply "$id"; done

# Inbox triage: tag important senders, archive newsletters, trash spam
nmail search --format ids tag:unread --quiet | nmail tag -- -unread -  # Mark all as read
nmail search --format ids tag:unread from:boss@company.com | nmail tag +important -
nmail search --format ids tag:unread subject:'weekly digest' | nmail archive -
nmail search --format ids subject:'viagra' | nmail trash -

# Reply to all flagged messages in batch
nmail search --format ids tag:flagged | while read id; do nmail reply "$id"; done

# Daily digest: what's new, what's pending
nmail search --format summary tag:unread --limit 10
nmail status
nmail log --since 1h --level error

# Find and forward all attachments from a sender
nmail search --format ids from:alice | while read id; do nmail forward "$id"; done

# Interactive contact picker → compose
nmail contacts | fzf --header='Pick recipient' | awk '{print $2}' | xargs nmail compose --to

# Render draft, diff against sent version
nmail render draft.md | diff - <(nmail open --raw 182)

# Watch for new mail, fire desktop notifications (via hooks)
nmail watch  # sits in background, fires on-new hook on new mail

# Auto-tag script: tag messages by sender domain rules
nmail search --format ids 'from:@company.com AND NOT tag:work' | nmail tag +work -

# Failed sends? Retry
nmail log --since 1h --event mail:error | grep -q . && nmail send --all

# Export all archived mail to mbox
find ~/Mail/archive/cur -type f | xargs cat > archive.mbox
```

## Agent Usage Patterns

### Read mail for the user

```bash
# Check new messages
nmail search --format summary tag:unread

# Open a specific message (identify by ID from search)
nmail open 182

# Search by sender
nmail search --format summary from:sender@domain
```

### Compose and send on behalf of user

```bash
# Compose (opens editor — for CLI-only, use --stdin)
echo -e "From: user\nTo: recipient@domain\nSubject: Test\n\n---\n\nBody here" | nmail compose --stdin

# Or programmatically create draft, then send
nmail compose --to recipient@domain --subject "Subject"
# ... user edits draft, saves
nmail send
```

### Check mailbox status

```bash
nmail status
nmail status --json
```

### Archive / organize

```bash
nmail search --format ids tag:unread --quiet | nmail tag -- -unread -  # Mark all as read
nmail search --format ids tag:unread | nmail archive -
nmail search --format ids from:bob | nmail tag +bob -
nmail tag +important 182
nmail trash 182
```

### Sync mail

```bash
nmail sync
```

## Invoking from Other Agents

- Use `nmail search --format json` for structured output to parse
- Use `nmail search --format ids` when piping to other nmail commands
- Use `nmail compose --stdin` for programmatic draft creation
- Use `nmail status --json` for structured mailbox stats
- Use `nmail open --raw` to get raw RFC5322 for programmatic parsing
- Non-interactive commands exit 0 on success, 1 on error — check exit codes
- Message IDs (like `182`) are partial-match: notmuch resolves them first, then Maildir glob fallback
- Search falls back to ripgrep/grep automatically when notmuch is unavailable
- `nmail compose --no-send` saves draft but skips queue; `nmail compose --queue` queues immediately after editor exit (default behavior)
