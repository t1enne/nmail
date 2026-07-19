# nmail — terminal-first mail toolkit

nmail is a composable Unix mail toolkit that treats email as plain data, letting you search, compose, automate, and process mail with shell pipelines instead of living inside a terminal UI. Unlike monolithic clients (mutt, aerc, sup), nmail doesn't own your screen — it provides 16 standalone subcommands that each do one thing and output to stdout. Compose with your editor on Markdown files. Send asynchronously through a queue. Search with notmuch or ripgrep. Hook into every event with shell scripts. No daemon, no database, no lock-in — just Maildir and pipes.

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
uv tool install git+https://github.com/nasrt/nmail

# Configure SMTP (required — without it you can't send)
$EDITOR ~/.msmtprc

# Configure IMAP (required — without it you can't receive)
$EDITOR ~/.mbsyncrc

# Configure nmail (optional — defaults work)
$EDITOR ~/.config/nmail/config.toml

# Sync and compose
nmail sync
nmail compose
nmail send
```

> **Full install guide:** [INSTALL.md](INSTALL.md) — system dependencies, all install methods, shell integration.
>
> **Configuration guide:** [CONFIG.md](CONFIG.md) — nmail config, msmtp, mbsync, notmuch, hooks, templates.

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

| Command          | Description                      |
| ---------------- | -------------------------------- |
| `nmail compose`  | Create/edit draft                |
| `nmail render`   | Markdown → RFC5322 MIME          |
| `nmail send`     | Send queued mail via msmtp       |
| `nmail sync`     | Sync Maildir via mbsync          |
| `nmail watch`    | Watch Maildir, fire events       |
| `nmail open`     | Open message in pager            |
| `nmail reply`    | Create reply draft               |
| `nmail forward`  | Create forward draft             |
| `nmail search`   | Search mail (notmuch or ripgrep) |
| `nmail tag`      | Add/remove notmuch tags          |
| `nmail archive`  | Move to archive                  |
| `nmail trash`    | Move to trash / empty trash      |
| `nmail contacts` | Extract/query contacts           |
| `nmail template` | Manage draft templates           |
| `nmail status`   | Mailbox statistics               |
| `nmail log`      | Query activity log               |
| `nmail attach`   | Manage saved attachments         |
| `nmail hook`     | Trigger hook scripts             |

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

See [CONFIG.md](CONFIG.md#7-directory-layout-after-setup) for the full layout.

## Configuration

See [CONFIG.md](CONFIG.md) for detailed configuration of nmail, msmtp, mbsync, notmuch, hooks, and templates.

Quick reference:

- `~/.config/nmail/config.toml` — nmail settings (flat top-level keys, no `[general]` section)
- `~/.msmtprc` — SMTP relay config (`chmod 600`)
- `~/.mbsyncrc` — IMAP sync config (`chmod 600`)
- `$EDITOR` / `$VISUAL` — editor for composing (read from env, not config)
- `NM_MAILDIR`, `NM_PAGER`, `NM_FROM`, `NM_SMTP_CMD`, `NM_CONFIG_HOME` — env overrides

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

See [INSTALL.md](INSTALL.md#1-system-dependencies) for OS-specific package install commands.

| Category        | Tools                                                                                           |
| --------------- | ----------------------------------------------------------------------------------------------- |
| **Required**    | Python ≥3.11, msmtp (SMTP send), mbsync (IMAP receive)                                          |
| **Recommended** | notmuch (fast search & tags), bat (pager), fzf (interactive browse)                             |
| **Optional**    | ripgrep (grep fallback), inotify-tools (efficient `watch`), notify-send (desktop notifications) |

## Documentation

Usage-focused docs in `doc/`:

- `doc/01-cli-spec.md` — Complete CLI specification (every subcommand, flag, output format)
- `doc/02-configuration.md` — TOML config format, hooks, env overrides
- `doc/03-composability.md` — Composability philosophy and pipe patterns
- `doc/04-example-pipelines.md` — Concrete shell pipeline recipes
- `doc/05-installation-and-e2e-guide.md` — End-to-end setup and guided walkthrough

## License

MIT
