# nmail — Installation & End-to-End Guide

> **Phase 0 (MVP) — done.** All commands via `nmail` single binary.

---

## 1. What nmail Is

nmail is a terminal-first mail client. Email lives in **Maildir** on disk, drafts are **Markdown**, every operation is a `nmail <subcommand>`. No GUI, no Electron, no IMAP in-process — it delegates to `mbsync` (IMAP sync), `msmtp` (SMTP send), `notmuch` (full-text search/index).

```
nmail search tag:unread | fzf | xargs nmail open
nmail search tag:todo | nmail archive -
nmail contacts alice | fzf | xargs nmail compose --to
```

---

## 2. Prerequisites

### Required

| Tool             | Purpose                         | Package             |
|------------------|----------------------------------|---------------------|
| **Python** ≥3.11 | Runtime                          | `python3`           |
| **msmtp**        | SMTP relay (send)                | `msmtp` / `msmtp-mta` |
| **mbsync**       | IMAP→Maildir sync                | `isync`             |

### Recommended

| Tool              | Purpose                              | Package           |
|-------------------|--------------------------------------|-------------------|
| **notmuch**       | Full-text mail index/search          | `notmuch`         |
| **bat**           | Syntax-highlighted pager             | `bat`             |
| **fzf**           | Interactive fuzzy finder             | `fzf`             |
| **ripgrep**       | Fallback search                      | `ripgrep`         |
| **inotify-tools** | Maildir watcher                      | `inotify-tools`   |
| **nvim / vim**    | Draft editor                         | `neovim` or `vim` |

### Install All at Once

**Debian/Ubuntu:**
```bash
sudo apt install -y python3 jq msmtp isync notmuch bat fzf ripgrep inotify-tools neovim
```

**Arch:**
```bash
sudo pacman -S python jq msmtp isync notmuch bat fzf ripgrep inotify-tools neovim
```

**macOS (Homebrew):**
```bash
brew install python jq msmtp isync notmuch bat fzf ripgrep neovim
```

---

## 3. Installation

```bash
# 1. Clone
git clone https://github.com/user/nmail ~/dev/nmail
cd ~/dev/nmail

# 2. Install via uv
uv sync

# 3. Verify
uv run nmail status
```

### What install does

- Installs `nmail` Python package via `uv`
- Provides `uv run nmail <subcommand>` or `uv tool install .` for global `nmail` command
- Creates Maildir tree at `~/Mail/` on first run
- Default config at `~/.config/nmail/config.toml` (auto-created)

---

## 4. Configuration

### 4.1 ~/.config/nmail/config.toml

```toml
[general]
maildir = "~/Mail"
editor = "nvim"
pager = "bat --plain --language=email"
file_browser = "lf"
from_address = "Your Name <you@example.com>"

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

```

### 4.2 ~/.msmtprc (SMTP)

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

account default : personal
```

**Permissions:** `chmod 600 ~/.msmtprc`

**Test:**
```bash
echo "Subject: test" | msmtp -a personal you@example.com
```

### 4.3 ~/.mbsyncrc (IMAP)

```
IMAPAccount personal
Host imap.example.com
User you@example.com
PassCmd "pass show mail/personal"
SSLType IMAPS

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

**Permissions:** `chmod 600 ~/.mbsyncrc`

**Test:**
```bash
mbsync personal
```

### 4.4 notmuch (optional)

```bash
notmuch setup
# database path: ~/Mail
# Tag new mail: +inbox +unread
# Tag sent mail: +sent
```

---

## 5. End-to-End: Sending Mail

### Step 1: Compose

```bash
nmail compose --to "alice@example.com" --subject "Project Update"
```

Editor opens a Markdown draft:

```
From: Your Name <you@example.com>
To: alice@example.com
Cc:
Subject: Project Update

---

# Weekly Status

- Deployed the new API endpoint
- Fixed the login timeout bug

Best,
Your Name
```

**Save and exit** — the draft is validated and queued.

### Step 2: Check queue

```bash
nmail status
# Queue: 1 pending, 0 failed
```

### Step 3: Render preview

```bash
nmail render ~/Mail/queue/new/<id>
```

### Step 4: Send

```bash
nmail send
# Sent: 1, Failed: 0
```

### Non-interactive compose

```bash
cat <<'EOF' | nmail compose --stdin --to "alice@example.com" --subject "Automated Report"
To: alice@example.com
Subject: Automated Report

---

Report generated. All systems nominal.
EOF
nmail send
```

---

## 6. End-to-End: Reading Mail

### Step 1: Sync

```bash
nmail sync
# 3 new messages
```

### Step 2: Search

```bash
# With notmuch
nmail search tag:unread
nmail search tag:unread from:alice

# Interactive fzf picker
nmail search --interactive tag:unread
```

### Step 3: Open

```bash
nmail open 182                    # by ID
nmail open ~/Mail/incoming/new/... # by path
nmail open --headers-only 182
```

### Step 4: Reply

```bash
nmail reply 182
# Opens editor with pre-filled headers + quoted original
# Save → queued → nmail send
```

### Step 5: Tagging

```bash
nmail tag +todo 182 193 204
nmail tag -unread 182
nmail search --format ids from:bob | nmail tag +bob -
```

### Step 6: Archive / Trash

```bash
nmail archive 182 193
nmail search --format ids tag:done | nmail archive -

nmail trash 182 193
nmail trash --empty --force
nmail trash --age 30 --force
```

---

## 7. Contacts

```bash
nmail contacts --update
nmail contacts alice
nmail contacts | fzf | cut -f2 | xargs nmail compose --to "{}"
```

---

## 8. Templates

```bash
nmail template list
nmail template create project-update
nmail template edit project-update
nmail template list | fzf | xargs nmail compose
```

---

## 9. Monitoring

```bash
nmail watch --once
nmail watch &

nmail log --follow
nmail log --since 1h
nmail log --event error --level 3

nmail status --watch
```

---

## 10. Daily Workflow

```bash
# Morning
nmail sync
nmail status

# Read new
nmail search --interactive tag:unread

# Reply
nmail reply 182
nmail send

# Compose
nmail compose --to "team@example.com" --subject "Daily standup notes"
nmail send

# Batch archive newsletters
nmail search --format ids subject:newsletter | nmail tag +newsletter -
nmail search --format ids tag:newsletter | nmail archive -

# Clean trash
nmail trash --age 30 --force
```

---

## 11. Troubleshooting

**nmail send: "msmtp not found"**
```bash
sudo apt install msmtp
```

**nmail sync: "mbsync not found"**
```bash
sudo apt install isync
```

**Queue failures:**
```bash
grep 'X-nmail-Error' ~/Mail/queue/cur/*
nmail send --all   # retry failed
```

---

## 12. Quick Reference

| Task               | Command                                                   |
|--------------------|-----------------------------------------------------------|
| Compose            | `nmail compose --to ADDR --subject TEXT`                  |
| Compose (stdin)    | `echo "draft" \| nmail compose --stdin --to ADDR`         |
| Render preview     | `nmail render ~/Mail/queue/new/FILE`                      |
| Send queue         | `nmail send`                                              |
| Sync mail          | `nmail sync`                                              |
| Status             | `nmail status`                                            |
| Search             | `nmail search QUERY`                                      |
| Interactive search | `nmail search --interactive`                              |
| Open               | `nmail open ID`                                           |
| Reply              | `nmail reply ID`                                          |
| Forward            | `nmail forward ID`                                        |
| Tag                | `nmail tag +tagname ID...`                                |
| Archive            | `nmail archive ID...`                                     |
| Trash              | `nmail trash ID...`                                       |
| Empty trash        | `nmail trash --empty --force`                             |
| Contacts           | `nmail contacts --update && nmail contacts QUERY`         |
| Templates          | `nmail template list/edit/create/delete`                  |
| Logs               | `nmail log --follow`                                      |
| Watch              | `nmail watch &`                                           |
| Attachments        | `nmail attach list/save ID PATH`                          |
| Fire hooks         | `nmail hook EVENT`                                        |
