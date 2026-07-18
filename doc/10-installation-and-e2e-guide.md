# nmail — Installation & End-to-End Guide

> **Phase 0 (MVP) — fully implemented.** All commands are functional bash scripts.

---

## 1. What nmail Is

nmail is a Unix-style terminal mail environment. Email lives in **Maildir** on disk, drafts are **Markdown**, every operation is a standalone shell command, and **tmux** provides the workspace. No GUI, no Electron, no IMAP in-process — it delegates to `mbsync` (IMAP sync), `msmtp` (SMTP send), `notmuch` (full-text search/index), and `pandoc` (Markdown→HTML rendering).

### Philosophy

```
mail-search tag:unread | fzf | xargs mail-open
mail-search tag:todo | mail-archive -
mail-contacts alice | fzf | xargs mail-compose --to
```

---

## 2. Prerequisites & Dependencies

### Required (hard dependency)

| Tool               | Purpose                                        | Package               |
| ------------------ | ---------------------------------------------- | --------------------- |
| **bash** ≥ 4.0     | All scripts are bash                           | Built-in              |
| **tmux**           | Session/workspace manager                      | `tmux`                |
| **jq**             | JSON parsing (logs, status, config extraction) | `jq`                  |
| **msmtp**          | SMTP relay (send mail)                         | `msmtp` / `msmtp-mta` |
| **mbsync** (isync) | IMAP→Maildir sync                              | `isync`               |

### Recommended

| Tool              | Purpose                                    | Package           |
| ----------------- | ------------------------------------------ | ----------------- |
| **notmuch**       | Full-text mail index/search                | `notmuch`         |
| **pandoc**        | Markdown→HTML (MIME multipart/alternative) | `pandoc`          |
| **bat**           | Syntax-highlighted pager                   | `bat`             |
| **fzf**           | Interactive fuzzy finder                   | `fzf`             |
| **ripgrep (rg)**  | Fallback search (when notmuch unavailable) | `ripgrep`         |
| **inotify-tools** | Maildir watcher (mail-watch)               | `inotify-tools`   |
| **nvim / vim**    | Draft editor                               | `neovim` or `vim` |

### Optional

| Tool            | Purpose                                           | Package     |
| --------------- | ------------------------------------------------- | ----------- |
| **lf**          | Terminal file browser (inbox pane)                | `lf`        |
| **pass**        | Password manager (`passwordeval` in msmtp/mbsync) | `pass`      |
| **notify-send** | Desktop notifications (hook scripts)              | `libnotify` |

### Install All at Once

**Debian/Ubuntu:**

```bash
sudo apt install -y tmux jq msmtp isync notmuch pandoc bat fzf ripgrep inotify-tools neovim lf pass libnotify-bin
```

**Arch Linux:**

```bash
sudo pacman -S tmux jq msmtp isync notmuch pandoc bat fzf ripgrep inotify-tools neovim lf pass libnotify
```

**macOS (Homebrew):**

```bash
brew install tmux jq msmtp isync notmuch pandoc bat fzf ripgrep inotify-tools neovim lf pass
```

**Fedora:**

```bash
sudo dnf install tmux jq msmtp isync notmuch pandoc bat fzf ripgrep inotify-tools neovim lf pass libnotify
```

---

## 3. Installation

```bash
# 1. Clone
git clone https://github.com/user/nmail ~/dev/nmail
cd ~/dev/nmail

# 2. Install (defaults to ~/.local prefix)
./install.sh

# 3. Add to PATH (add to ~/.bashrc or ~/.zshrc permanently)
export PATH="$HOME/.local/bin:$PATH"

# Verify
which mail-compose    # → ~/.local/bin/mail-compose
mail-status           # → shows empty Maildir stats
```

### What `install.sh` does

- Symlinks **19 commands** from `bin/` → `~/.local/bin/`
- Copies **4 libraries** (`common.sh`, `maildir.sh`, `notmuch.sh`, `render.sh`) → `~/.local/lib/nmail/`
- Copies `config.toml` → `~/.config/nmail/` (never overwrites)
- Copies hook scripts (`on-new`, `on-sent`, `on-error`) → `~/.config/nmail/hooks.d/`
- Creates full **Maildir tree** at `~/Mail/`
- Creates **state directory** at `~/.local/state/nmail/`
- Copies default templates (`default.md`, `reply.md`, `forward.md`) → `~/Mail/templates/`

---

## 4. Configuration

### 4.1 ~/.config/nmail/config.toml

```toml
[general]
maildir = "~/Mail"
editor = "nvim"
pager = "bat --plain --language=email"
file_browser = "lf"
markdown_converter = "pandoc -f markdown -t html"
from_address = "Your Name <you@example.com>"
signature = ""

[smtp]
command = "msmtp"

[queue]
process_interval = 60
max_retries = 3
retry_delay = 300

[sync]
tool = "mbsync"
accounts = []
interval = 300

[notmuch]
enabled = true
command = "notmuch"

[hooks]
dir = "~/.config/nmail/hooks.d/"
enabled = true

[tmux]
session = "mail"
layout = "grid"
command = "tmux"
```

**Key fields to set:**

- `general.from_address` — your default From: address
- `general.editor` — `nvim`, `vim`, `nano`, `code --wait`, etc.
- `general.pager` — `bat --plain --language=email` or `less`

### 4.2 ~/.msmtprc (SMTP — for sending)

```
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        ~/Mail/logs/send.log

account personal
host           smtp.example.com
port           587
from           you@example.com
user           you@example.com
passwordeval   pass show mail/personal

# For Gmail:
# account gmail
# host           smtp.gmail.com
# port           587
# from           you@gmail.com
# user           you@gmail.com
# passwordeval   pass show mail/gmail

account default : personal
```

**Set permissions:** `chmod 600 ~/.msmtprc`

**Test SMTP:**

```bash
echo "Subject: test" | msmtp -a personal you@example.com
```

### 4.3 ~/.mbsyncrc (IMAP — for receiving)

```
IMAPAccount personal
Host imap.example.com
User you@example.com
PassCmd "pass show mail/personal"
SSLType IMAPS
# For self-signed certs: CertificateFile ~/.cert/imap.pem

IMAPStore personal-remote
Account personal

MaildirStore personal-local
Path ~/Mail/incoming/
Inbox ~/Mail/incoming/

Channel personal
Far :personal-remote:
Near :personal-local:
Patterns *
Create Near
Sync All
Expunge Both
```

**Set permissions:** `chmod 600 ~/.mbsyncrc`

**Test IMAP:**

```bash
mbsync personal    # sync a single account
mbsync -a          # sync all accounts
```

### 4.4 notmuch (optional — search index)

```bash
notmuch setup
# database path: ~/Mail
# Your name: Your Name
# Your email: you@example.com
# Tag new mail: +inbox +unread
# Tag sent mail: +sent
```

---

## 5. End-to-End: Sending Mail

### Step 1: Compose a draft

```bash
# Interactive (opens $EDITOR)
mail-compose --to "alice@example.com" --subject "Project Update"

# From template
mail-compose --template default --to "alice@example.com" --subject "Quick note"
```

The editor opens a Markdown draft:

```
From: Your Name <you@example.com>
To: alice@example.com
Cc:
Subject: Project Update

---

# Weekly Status

- Deployed the new API endpoint
- Fixed the login timeout bug
- Meeting tomorrow at 2pm

Best,
Your Name
```

- **Save and exit** — the draft is validated and queued.
- If `To:` is empty, validation fails and the draft is saved to `~/Mail/drafts/` for fixing.

### Step 2: Check the queue

```bash
mail-status
```

Output:

```
Incoming:    0 new, 0 total
Archive:     0 total
Sent:        0 total
Drafts:      0 pending
Queue:       1 pending, 0 failed
Trash:       0 total
Last sync:   never
```

### Step 3: Render (optional — preview what gets sent)

```bash
ls ~/Mail/queue/new/           # find the queue file
mail-render ~/Mail/queue/new/1760045622.12345.hostname
```

This outputs the full MIME message (multipart/alternative with text/plain + text/html).

### Step 4: Send

```bash
mail-send
```

Output:

```
  ✓ 1760045622.12345.hostname
Sent: 1, Failed: 0
```

### Alternative: Compose non-interactively (from stdin)

```bash
cat <<'EOF' | mail-compose --stdin --to "alice@example.com" --subject "Automated Report"
From: Your Name <you@example.com>
To: alice@example.com
Subject: Automated Report

---

Report generated at $(date). All systems nominal.
EOF
```

### Alternative: Compose → render → send as pipeline

```bash
mail-compose --to "team@example.com" --subject "Daily Digest" --stdin < digest.md
mail-send
```

---

## 6. End-to-End: Reading Mail

### Step 1: Sync from IMAP

```bash
mail-sync
```

Output:

```
mail-sync: 3 new messages
```

This runs `mbsync -a`, then `notmuch new` for indexing, then fires hooks.

### Step 2: Check status

```bash
mail-status
```

### Step 3: Search

```bash
# With notmuch (tag-based search)
mail-search tag:unread
mail-search tag:unread from:alice
mail-search tag:unread subject:invoice

# With ripgrep fallback (no notmuch needed)
mail-search "urgent"

# Interactive fzf picker
mail-search --interactive tag:unread
# Opens fzf with preview pane showing the email content
# Select → opens in pager
```

### Step 4: Open

```bash
# By ID
mail-open 182                    # resolves via notmuch, opens in $PAGER

# By file path
mail-open ~/Mail/incoming/new/1760045622.12345.hostname

# Headers only
mail-open --headers-only 182

# Raw RFC822
mail-open --raw 182
```

### Step 5: Reply

```bash
mail-reply 182
```

Opens `$EDITOR` with pre-filled headers and quoted original:

```
From: Your Name <you@example.com>
To: alice@example.com
Cc:
Subject: Re: Project Update
In-Reply-To: <original-message-id>
References: <original-message-id>

---

On Mon, 14 Jul 2026 10:30:00 +0000, Alice wrote:

> Here's the project update...

Your reply here.
```

Save and exit — draft is validated and queued. Then: `mail-send`

### Step 6: Reply to all

```bash
mail-reply --all 182
```

### Step 7: Forward

```bash
mail-forward 182
```

Opens editor with:

```
From: Your Name <you@example.com>
To:
Subject: Fwd: Project Update

---

---------- Forwarded message ---------
From: Alice <alice@example.com>
Date: Mon, 14 Jul 2026 10:30:00 +0000
Subject: Project Update
To: You <you@example.com>

> [original message content]
```

### Step 8: Tagging

```bash
# Add tag
mail-tag +todo 182 193 204

# Remove tag
mail-tag -unread 182

# Pipeline: tag all from Bob
mail-search --format ids from:bob | mail-tag +bob -
```

### Step 9: Archive

```bash
# Archive by ID
mail-archive 182 193

# Pipeline: archive all with tag "done"
mail-search --format ids tag:done | mail-archive -

# Tag + archive in one command
mail-archive --tag done 182
```

### Step 10: Trash

```bash
# Move to trash
mail-trash 182 193

# Pipeline
mail-search --format ids subject:spam | mail-trash -

# Empty trash
mail-trash --empty --force

# Remove trash older than 30 days
mail-trash --age 30 --force
```

---

## 7. Contacts

```bash
# Build contact database from all mail headers
mail-contacts --update

# Search
mail-contacts alice
# Output: Alice Smith   alice@example.com   42

# Interactive: pick contact → compose
mail-contacts | fzf | cut -f2 | xargs mail-compose --to "{}"

# JSON output
mail-contacts --format json alice
```

---

## 8. Templates

```bash
# List templates
mail-template list

# Create from scratch
mail-template create project-update

# Edit
mail-template edit project-update

# View
mail-template show reply

# Compose from template
mail-template list | fzf | xargs mail-compose
```

---

## 9. The tmux Workspace

```bash
mail-session
```

This launches a tmux session with 4 panes in a grid:

```
┌──────────────────────┬──────────────────────┐
│  compose (nvim)      │  inbox (lf/ranger)   │
│  ~/Mail/drafts/      │  ~/Mail/incoming/    │
├──────────────────────┼──────────────────────┤
│  shell + status      │  search              │
│  mail-status + logs  │  mail-search --inter │
└──────────────────────┴──────────────────────┘
```

**Options:**

```bash
mail-session --layout windows   # separate tmux windows per function
mail-session --no-sync          # skip initial sync
mail-session --no-watch         # don't start watcher
mail-session --project work     # custom session name
```

**Re-attach:**

```bash
tmux attach -t mail
```

---

## 10. Monitoring

### mail-watch (live notifications)

```bash
# Run once
mail-watch --once

# Run continuously (daemon)
mail-watch &

# In systemd user service
# ~/.config/systemd/user/nmail-watch.service:
# [Service]
# ExecStart=%h/.local/bin/mail-watch
# Restart=always
```

### mail-log

```bash
# Tail log
mail-log --follow

# Filter by event
mail-log --event mail:new

# Last hour
mail-log --since 1h

# Errors only
mail-log --level 3

# JSON output
mail-log --json --event mail:sent
```

### mail-status --watch

```bash
mail-status --watch    # refreshes every 5 seconds
```

---

## 11. Complete Daily Workflow

```bash
# Morning: sync and check
mail-sync
mail-status

# Read new mail interactively
mail-search --interactive tag:unread

# Reply to something
mail-reply 182          # edit, save → auto-queued
mail-send               # drain queue

# Compose new
mail-compose --to "team@example.com" --subject "Daily standup notes"
# edit, save → auto-queued
mail-send

# Batch: archive read newsletters
mail-search --format ids tag:unread subject:newsletter | mail-tag +newsletter -
mail-search --format ids tag:newsletter | mail-archive -

# Clean up
mail-trash --age 30 --force     # auto-delete old trash

# Launch workspace
mail-session
```

---

## 12. Troubleshooting

### mail-send: "msmtp not found"

```bash
sudo apt install msmtp        # Debian/Ubuntu
brew install msmtp            # macOS
```

### mail-sync: "mbsync not found"

```bash
sudo apt install isync        # Debian/Ubuntu
brew install isync            # macOS
```

### mail-compose: "Missing To: header"

The draft validation requires `To:` and `Subject:` headers. Check your draft in `~/Mail/drafts/`.

### mail-search: "notmuch not available"

Install notmuch and run `notmuch setup`. Fallback uses ripgrep or grep.

### Draft not queuing

Check if `To:` is empty. Drafts that fail validation are saved to `~/Mail/drafts/` with error messages.

### Queue shows failed messages

Check `~/Mail/queue/cur/` for failed messages. Each has `X-nmail-Error:` headers appended.

```bash
grep 'X-nmail-Error' ~/Mail/queue/cur/*
```

Re-send with `mail-send --all` or retry individual IDs.

---

## 13. Architecture Overview

```
Compose (mail-compose)
  └─ Markdown draft → ~/Mail/drafts/*.md
       └─ Validated → ~/Mail/queue/new/
            └─ Rendered (mail-render) → MIME
                 └─ Sent (mail-send) → msmtp → SMTP server
                      └─ Moved to ~/Mail/sent/cur/

Receive (mail-sync)
  └─ mbsync → ~/Mail/incoming/new/
       └─ notmuch index
            └─ hooks.d/on-new fires

Search (mail-search)
  └─ notmuch (or rg fallback) → file paths
       └─ fzf (interactive) or stdout (pipeable)

Watch (mail-watch)
  └─ inotifywait on incoming/new/ + queue/new/
       └─ log_event + hooks
```

---

## 14. Quick Reference Card

| Task               | Command                                                         |
| ------------------ | --------------------------------------------------------------- |
| Compose            | `mail-compose --to ADDR --subject TEXT`                         |
| Compose (stdin)    | `echo "draft" \| mail-compose --stdin --to ADDR --subject TEXT` |
| Render preview     | `mail-render ~/Mail/queue/new/FILE`                             |
| Send queue         | `mail-send`                                                     |
| Sync mail          | `mail-sync`                                                     |
| Status             | `mail-status` (or `mail-status --json \| jq`)                   |
| Search             | `mail-search QUERY`                                             |
| Interactive search | `mail-search --interactive`                                     |
| Open               | `mail-open ID`                                                  |
| Reply              | `mail-reply ID`                                                 |
| Reply all          | `mail-reply --all ID`                                           |
| Forward            | `mail-forward ID`                                               |
| Tag                | `mail-tag +tagname ID...`                                       |
| Archive            | `mail-archive ID...`                                            |
| Trash              | `mail-trash ID...`                                              |
| Empty trash        | `mail-trash --empty --force`                                    |
| Contacts           | `mail-contacts --update && mail-contacts QUERY`                 |
| Templates          | `mail-template list/edit/create/delete`                         |
| Logs               | `mail-log --follow`                                             |
| Watch              | `mail-watch &`                                                  |
| Launch workspace   | `mail-session`                                                  |
| Attachments        | `mail-attach list/save ID PATH`                                 |
| Fire hooks         | `mail-hook EVENT`                                               |
