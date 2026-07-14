# Plugin & Hook Architecture

## Overview

Two extension mechanisms:

1. **Hooks** — simple shell scripts triggered by events. Lightweight, zero-config.
2. **Plugins** — packaged hooks with dependencies and metadata. Discoverable, installable.

## Hook System

### Event Types

| Event | Trigger | Args |
|---|---|---|
| `mail:new` | New messages in incoming/new/ | `count` |
| `mail:sent` | Message successfully sent | `queue-id` |
| `mail:error` | Send failure | `queue-id`, `error-message` |
| `mail:sync-start` | Sync begins | (none) |
| `mail:sync-end` | Sync completes | `new-count` |
| `mail:draft` | Draft saved to drafts/ or queue/ | `draft-path` |
| `mail:trash` | Message moved to trash | `message-path` |
| `mail:archive` | Message moved to archive | `message-path` |
| `mail:tag` | Tag added/removed | `operation (+/-)`, `tag`, `message-id` |

### Hook Execution

```
mail-sync completes
    │
    ▼
mail-hook mail:sync-end 3
    │
    ▼
for each executable in ~/.config/nmail/hooks.d/ matching "sync-end":
    exec ./on-sync-end "mail:sync-end" "3"
    │
    ├─ exit 0 → continue
    └─ exit non-zero → log warning, continue to next hook
```

Hooks never block the main operation. Non-zero exits are logged but don't abort.

### Hook Directory Structure

```
~/.config/nmail/hooks.d/
├── on-new              # chmod +x
├── on-sent
├── on-error
├── on-sync-start
├── on-sync-end
├── on-draft
├── on-trash
└── on-archive
```

Each file must be executable. Naming convention: `on-<event-short-name>`. Only the short name matters (after `on-`); multiple hooks for same event can exist with suffixes: `on-new-notify`, `on-new-index`.

### Built-in Hook Examples

**on-new (notification):**
```bash
#!/bin/bash
# $1 = "mail:new", $2 = count
count="${2:-0}"
if (( count > 0 )); then
    notify-send "📬 New Mail" "$count new message(s)" \
        --icon=mail-unread \
        --category=email
fi
```

**on-new (index):**
```bash
#!/bin/bash
# Re-index notmuch after new mail
if command -v notmuch &>/dev/null; then
    notmuch new 2>/dev/null
fi
```

**on-sent (log):**
```bash
#!/bin/bash
# $1 = "mail:sent", $2 = queue-id
echo "[$(date -Iseconds)] sent $2" >> ~/.mail-activity.log
```

**on-error (alert + retry):**
```bash
#!/bin/bash
# $1 = "mail:error", $2 = queue-id, $3 = error
id="$2"
err="$3"
notify-send -u critical "❌ Mail Send Failed" "$id: $err"

# Queue for retry in 5 minutes
echo "$id" >> /tmp/nmail-retry-queue
```

**on-sync-end (summary):**
```bash
#!/bin/bash
# $1 = "mail:sync-end", $2 = count
count="${2:-0}"
echo "[$(date -Iseconds)] sync: $count new" >> ~/Mail/logs/sync.log
```

## Plugin System

### Plugin Definition

A plugin is a directory containing at minimum a `plugin.toml` manifest:

```
~/.config/nmail/plugins/<name>/
├── plugin.toml          # Required: metadata
├── hooks.d/             # Optional: hook scripts
│   ├── on-new
│   └── on-sent
├── scripts/             # Optional: helper scripts
│   └── helper.sh
└── README.md            # Optional: documentation
```

### `plugin.toml` Format

```toml
[plugin]
name = "my-plugin"
version = "1.0.0"
description = "Short description of what this plugin does"
author = "Name <email>"
homepage = "https://github.com/user/my-nmail-plugin"
license = "MIT"

# Dependencies: commands that must exist
[requirements]
commands = ["notify-send", "jq"]
# Optional: minimum versions
# [requirements.versions]
# jq = "1.6"

# Hooks this plugin provides
[hooks]
"mail:new" = "hooks.d/on-new"
"mail:error" = "hooks.d/on-error"

# Configuration defaults
[config]
notify_sound = true
notify_urgency = "normal"

# Conflicts with other plugins
conflicts = ["other-notification-plugin"]
```

### Plugin Installation

```bash
# Install from directory
mail-plugin install ./my-plugin/

# Install from git
mail-plugin install https://github.com/user/nmail-plugin-notify

# List installed plugins
mail-plugin list

# Enable/disable
mail-plugin enable my-plugin
mail-plugin disable my-plugin

# Remove
mail-plugin remove my-plugin
```

### Plugin Loading

On startup, `mail-session` (and any command that fires hooks):

1. Read `~/.config/nmail/config.toml` → `plugins.enabled`
2. For each enabled plugin:
   a. Read its `plugin.toml`
   b. Check `requirements.commands` exist
   c. Symlink `hooks.d/*` → `~/.config/nmail/hooks.d/`
   d. Source `scripts/` into PATH

### Plugin Discovery

Plugins can be listed via:

```bash
mail-plugin search            # Search known plugin index
mail-plugin search notify     # Search with query
```

## `mail-plugin` Command

```
mail-plugin <operation> [args]

Manage nmail plugins.

Operations:
  install PATH|URL    Install plugin from directory or git URL
  remove NAME         Uninstall plugin
  list                List installed plugins
  enable NAME         Enable a disabled plugin
  disable NAME        Disable a plugin (keep installed)
  info NAME           Show plugin details
  update NAME         Update plugin from source (git pull)
  search QUERY        Search remote plugin index

Examples:
  mail-plugin install ~/dev/nmail-plugin-gpg
  mail-plugin install https://github.com/user/nmail-plugin-notify
  mail-plugin list
  mail-plugin enable my-plugin
```

## Standard Plugin Ideas

| Plugin | Description | Hooks |
|---|---|---|
| `notify-desktop` | Desktop notifications via notify-send | mail:new, mail:error |
| `notify-telegram` | Telegram notifications via bot API | mail:new, mail:error |
| `auto-archive` | Archive messages matching rules | mail:new |
| `gpg-sign` | GPG-sign outgoing messages | mail:sent (pre-send hook) |
| `spam-filter` | Move spam to trash via rules | mail:new |
| `backup` | Backup Maildir to remote | mail:sync-end |
| `stats` | Generate mail statistics | mail:sync-end |
| `vacation` | Auto-reply when away | mail:new |
| `attachment-scan` | Virus scan attachments | mail:draft |
| `contacts-sync` | Sync contacts with CardDAV | mail:sync-end |
| `label-colors` | Color-coded notmuch tags | mail:tag |

## Hook Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      EVENT SOURCE                            │
│  mail-sync, mail-send, mail-compose, mail-tag, etc.         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    mail-hook <event> <args>                   │
│                                                              │
│  1. Log event to ~/Mail/logs/mail.log                        │
│  2. Find matching hooks in ~/.config/nmail/hooks.d/         │
│  3. Run each matching executable in sequence                 │
│  4. Collect exit codes, log failures                         │
│  5. Return 0 (always) — hooks never block main flow          │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ on-new   │   │ on-new-  │   │ on-new-  │
    │          │   │ notify   │   │ index    │
    │ exit 0   │   │ exit 0   │   │ exit 1   │
    └──────────┘   └──────────┘   └──────────┘
                          │               │
                          ▼               ▼
                    notification    log warning:
                    sent            "on-new-index
                                    failed (exit 1)"
```

## Pre/Post Hook Distinction

For operations that support it (e.g., `mail-send`), hooks can be pre or post:

```
~/.config/nmail/hooks.d/
├── pre-send-gpg        # Runs BEFORE mail-render
├── on-sent-log         # Runs AFTER successful send
└── on-error-retry      # Runs AFTER failed send
```

Pre hooks can modify the draft. Post hooks cannot affect the operation.

Pre hooks receive the draft file path as `$3`. They can modify it in-place. Exit non-zero to abort the operation.

```bash
#!/bin/bash
# pre-send-gpg — sign the draft before sending
# $1 = mail:pre-send
# $2 = queue-id
# $3 = draft file path (in queue/tmp/)

gpg --sign --armor "$3"
```
