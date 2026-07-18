---
name: nmail
description: Terminal-first mail client — compose, search, reply, tag, and manage email via CLI. Use when the user needs to read email, compose messages, search mail, manage tags, reply/forward, sync IMAP, check mailbox status, watch for new mail, or manage templates/attachments.
allowed-tools: Bash(nmail:*)
---

# nmail — Terminal Mail Client

`nmail` is a Python CLI tool that treats email as data (Maildir + Markdown). Every subcommand is a standalone action — composable with pipes, fzf, and shell pipelines.

## Quick Reference

```bash
nmail --help                          # List all subcommands
nmail sync                            # Fetch mail via mbsync
nmail search --interactive            # Browse mail with fzf preview
nmail compose --to alice@example.com  # Compose new message
nmail reply 182                       # Reply to message ID 182
nmail send                            # Send queued messages
nmail open 182                        # Open message in pager
nmail status                          # Mailbox statistics
nmail tag +todo 182                   # Add "todo" tag
nmail archive 182                     # Archive message
nmail trash 182                       # Trash message
nmail contacts alice                  # Search contacts
nmail watch                           # Watch for new mail
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

**Output formats:** `summary` (default, date/from/subject table), `ids` (message IDs), `files` (full paths), `json`, `preview` (full rendered)

**Pipe pattern:**
```bash
nmail search --format ids tag:unread | xargs nmail open
nmail search --format ids tag:todo | nmail archive -
nmail search --format ids tag:unread | nmail tag +read -
```

### Open

Open message in pager (bat if available, otherwise configured pager).

```bash
nmail open 182                       # Open by message ID
nmail open ~/Mail/incoming/new/...   # Open by file path
nmail open --headers-only 182        # Show headers only
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
nmail tag +todo 182                  # Add tag (must start with +)
nmail tag -unread 182                # Remove tag (must start with -)
nmail tag +work 182 193 204          # Tag multiple messages
nmail search --format ids from:bob | nmail tag +bob -   # Tag from pipe
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

Manage saved attachments in `~/Mail/attachments/`.

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
└── config.toml          # Main configuration
└── hooks.d/             # Event hooks (on-new, on-sent, on-error)

~/Mail/
├── incoming/{cur,new,tmp}/   # Inbox
├── archive/cur/              # Archived messages
├── drafts/*.md               # Drafts (Markdown)
├── sent/{cur,new,tmp}/       # Sent mail
├── trash/{cur,new,tmp}/      # Trash
├── queue/{cur,new,tmp}/      # Outgoing queue
├── templates/*.md            # Draft templates
├── attachments/              # Saved attachments
└── logs/                     # Event logs (nmail.log)
```

## Configuration

```toml
# ~/.config/nmail/config.toml
[general]
maildir = "~/Mail"
editor = "nvim"
pager = "bat --plain --language=email"
from_address = "John Doe <john@example.com>"

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

## Dependencies

**Required:** Python ≥3.11, click≥8.1, tomli≥2.0
**Recommended:** msmtp (SMTP), mbsync (IMAP), notmuch (search), nvim (editor), bat (pager), fzf (picker), lf (file browser), inotify-tools (watch), ripgrep (search fallback)
**Install:** `uv tool install .` or `uv run nmail --help` for dev

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
nmail search --format ids tag:unread | nmail archive -
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
- Message IDs (like `182`) are partial-match — notmuch resolves them to full paths
