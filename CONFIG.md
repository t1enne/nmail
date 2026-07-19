# Configuring nmail

nmail delegates sending to **msmtp** and receiving to **mbsync**. You must configure those tools separately. nmail's own config file is optional — sensible defaults cover most cases.

---

## 1. nmail Configuration

**File:** `~/.config/nmail/config.toml` (TOML format, auto-created on first run)

All keys are flat at the top level — no `[general]` section.

```toml
# ~/.config/nmail/config.toml

# Maildir root. Default: ~/Mail
maildir = "~/Mail"

# Pager for reading mail. Default: $PAGER or less
pager = "bat --plain --language=email"

# Maximum search results
search_limit = 100

[user]
# Default From: address. Default: $EMAIL env var
from = "Your Name <you@example.com>"

[smtp]
# SMTP send command. Default: msmtp
command = "msmtp"

[sync]
# Sync tool. Default: mbsync
tool = "mbsync"

# Accounts to sync (names must match ~/.mbsyncrc Channels)
accounts = ["personal"]

# Sync interval in seconds for nmail watch. 0 = manual only.
interval = 300

[notmuch]
# Enable notmuch integration for search and tags
enabled = true

# notmuch binary path
command = "notmuch"

[templates]
# Draft template directory
dir = "~/Mail/templates"

# Default template name (file at $dir/default.md)
default = "default"

[hooks]
# Enable hook scripts
enabled = true

# Hook scripts directory
dir = "~/.config/nmail/hooks.d"

[logging]
# Log directory
dir = "~/Mail/logs"

# Log level: debug, info, warn, error
level = "info"

[notifications]
# Desktop notifications (via notify-send)
enabled = true

# Only fire for these events (empty = all)
events = ["mail:new", "mail:error"]
```

### Environment variable overrides

Every config key can be set via environment:

| Variable | Overrides |
|---|---|
| `NM_MAILDIR` | `maildir` |
| `NM_PAGER` | `pager` |
| `NM_FROM` | `user.from` |
| `NM_SMTP_CMD` | `smtp.command` |
| `NM_CONFIG_HOME` | Config directory path (alt to `~/.config/nmail`) |

Editor is read from `$EDITOR` or `$VISUAL` env vars, **not** from the config file.

---

## 2. SMTP: msmtp

**File:** `~/.msmtprc`

```
# ~/.msmtprc
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

account work
host           smtp.company.com
port           587
from           you@company.com
user           you@company.com
passwordeval   pass show mail/work

# Default sending account
account default : personal
```

**Permissions:** `chmod 600 ~/.msmtprc`

### Password options

```bash
# Plaintext (least safe):
password mypassword

# Password file:
passwordeval "cat ~/.mail-pass"

# pass password manager:
passwordeval "pass show mail/personal"

# macOS Keychain:
passwordeval "security find-generic-password -a you@example.com -s mail -w"

# GPG-encrypted file:
passwordeval "gpg --decrypt ~/.mail-pass.gpg"
```

### Test

```bash
echo "Subject: test" | msmtp -a personal you@example.com
```

If you receive the test email, msmtp is working.

### Common SMTP settings

| Provider | Host | Port |
|---|---|---|
| Gmail | `smtp.gmail.com` | 587 |
| Fastmail | `smtp.fastmail.com` | 587 |
| Proton Mail | Use [Proton Mail Bridge](https://proton.me/mail/bridge) | |
| Office 365 | `smtp.office365.com` | 587 |
| iCloud | `smtp.mail.me.com` | 587 |

Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

---

## 3. IMAP: mbsync

**File:** `~/.mbsyncrc`

```
# ~/.mbsyncrc

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

### Test

```bash
mbsync personal
```

After sync, check `~/Mail/incoming/new/` — it should contain message files.

### Multiple accounts

```toml
# ~/.config/nmail/config.toml
[sync]
accounts = ["personal", "work"]
```

Each account name must match a Channel in `~/.mbsyncrc`. nmail runs `mbsync <account>` for each.

### Common IMAP settings

| Provider | Host | Port |
|---|---|---|
| Gmail | `imap.gmail.com` | 993 |
| Fastmail | `imap.fastmail.com` | 993 |
| Proton Mail | Use [Proton Mail Bridge](https://proton.me/mail/bridge) | |
| Office 365 | `outlook.office365.com` | 993 |
| iCloud | `imap.mail.me.com` | 993 |

Enable IMAP access in your provider settings first. Gmail requires an App Password.

### Gmail: sync Spam and other labels

By default mbsync only syncs `INBOX`. To sync other Gmail labels:

```
Channel personal
Far :personal-remote:
Near :personal-local:
Patterns "INBOX" "[Gmail]/Sent Mail" "[Gmail]/Drafts" "[Gmail]/Trash" "[Gmail]/Archive" "[Gmail]/Spam"
Create Near
Sync All
Expunge Both
```

After updating Patterns, run `mbsync personal` and `notmuch new`.

---

## 4. notmuch (search and tags)

notmuch indexes your Maildir for fast search. Not strictly required — nmail falls back to ripgrep/grep — but recommended for tag-based workflows.

### Setup

```bash
notmuch setup
```

When prompted:

```
Path to directory: ~/Mail
Tags to add to new messages: +inbox +unread
Tags to add to sent messages: +sent
```

### Verify

```bash
notmuch new       # index new messages
notmuch count tag:unread
nmail search tag:unread
```

nmail's `tag`, `search`, `archive` commands use notmuch. Without it, `tag` is unavailable, `search` falls back to grep over Maildir, and `archive` moves files directly.

### Regular indexing

Run `notmuch new` after each `mbsync`. nmail's `nmail sync` does both:

```bash
nmail sync
# → mbsync personal
# → notmuch new
```

---

## 5. Hooks

nmail fires hook scripts on events. Scripts live in `~/.config/nmail/hooks.d/`.

**File:** `~/.config/nmail/hooks.d/on-new` (example)

```bash
#!/bin/bash
# $1 = event name (e.g. "mail:new")
# $2 = count of new messages
count="$2"
notify-send "nmail" "$count new message(s)" --icon=mail-unread
```

Make it executable: `chmod +x ~/.config/nmail/hooks.d/on-new`

### Available hook events

| Hook script | Triggered when |
|---|---|
| `on-new` | New mail arrives (`nmail watch` or after sync) |
| `on-sent` | Message sent successfully |
| `on-error` | Send fails (`$3` = error message) |
| `on-sync-start` | Sync begins |
| `on-sync-end` | Sync completes |
| `on-draft` | Draft saved |
| `on-trash` | Message moved to trash |
| `on-archive` | Message archived |

### Test hooks

```bash
nmail hook new 3          # fire on-new with count 3
nmail hook sent abc123    # fire on-sent with message id
```

---

## 6. Draft Templates

nmail creates Markdown drafts from templates. Templates live in `~/Mail/templates/`.

Three built-in templates (`default`, `reply`, `forward`) are bundled. To customize:

```bash
nmail template list           # list available templates
nmail template show default   # view a template
nmail template create custom  # create new (opens $EDITOR)
nmail template edit reply     # edit an existing one
```

Template variables:

| Variable | Expands to |
|---|---|
| `{{from}}` | `user.from` config value |
| `{{date}}` | Current date (ISO 8601) |

---

## 7. Directory Layout After Setup

```
~/.config/nmail/
├── config.toml          # nmail config
└── hooks.d/             # hook scripts (optional)

~/.msmtprc               # SMTP config
~/.mbsyncrc              # IMAP config

~/Mail/
├── incoming/{cur,new,tmp}/   # Synced inbox
├── archive/cur/              # Archived messages
├── drafts/*.md               # Drafts in progress
├── sent/{cur,new,tmp}/       # Sent mail
├── trash/{cur,new,tmp}/      # Trash
├── queue/{cur,new,tmp}/      # Outgoing queue
├── templates/*.md            # Draft templates
├── attachments/              # Saved attachments
└── logs/
    └── nmail.log             # JSON-line event log
```
