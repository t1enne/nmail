# Process Flows

## Flow 1: Compose → Queue → Send

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: COMPOSE                                                  │
│                                                                  │
│   nmail compose [draft.md]                                       │
│       │                                                          │
│       ├─ No arg: open $EDITOR on ~/Mail/drafts/<timestamp>.md    │
│       ├─ Arg:    open $EDITOR on specified file                  │
│       │                                                          │
│       ▼                                                          │
│   $EDITOR opens draft.md                                         │
│       │                                                          │
│       │  File format:                                            │
│       │  ┌──────────────────────────────┐                        │
│       │  │ To: alice@example.com        │                        │
│       │  │ Cc:                          │                        │
│       │  │ Bcc:                         │                        │
│       │  │ Subject: Meeting notes       │                        │
│       │  │                              │                        │
│       │  │ ---                          │                        │
│       │  │                              │                        │
│       │  │ Markdown body here.          │                        │
│       │  │                              │                        │
│       │  │ - bullets                    │                        │
│       │  │ - **bold**                   │                        │
│       │  │                              │                        │
│       │  │ /path/to/attachment.pdf      │                        │
│       │  └──────────────────────────────┘                        │
│       │                                                          │
│       ▼                                                          │
│   User saves and closes $EDITOR                                  │
│       │                                                          │
│       ▼                                                          │
│   nmail compose validates:                                       │
│       ├─ To: header present?                                     │
│       ├─ Subject: present?                                       │
│       └─ Body non-empty?                                         │
│       │                                                          │
│       ├─ Valid → copy to ~/Mail/queue/new/<id>                   │
│       │          log "mail:draft <id>"                           │
│       │          exit 0                                          │
│       │                                                          │
│       └─ Invalid → warn, keep draft.md, exit 1                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: QUEUE                                                    │
│                                                                  │
│   Queue directory: ~/Mail/queue/                                 │
│                                                                  │
│   queue/new/<id>     ← pending (Maildir new/)                    │
│   queue/tmp/<id>     ← being processed                           │
│   queue/cur/<id>     ← processed (sent ok or failed)             │
│                                                                  │
│   Queue file format (RFC822-ish preamble + markdown):            │
│   ┌──────────────────────────────────────────┐                   │
│   │ From: user@domain.com                    │                   │
│   │ To: alice@example.com                    │                   │
│   │ Cc:                                      │                   │
│   │ Bcc:                                     │                   │
│   │ Subject: Meeting notes                   │                   │
│   │ Date: Sun, 13 Jul 2026 14:30:00 +0000    │                   │
│   │ Message-ID: <20260713...@domain>         │                   │
│   │ X-nmail-Status: pending                  │                   │
│   │                                          │                   │
│   │ ---                                      │                   │
│   │                                          │                   │
│   │ Markdown body...                         │                   │
│   │                                          │                   │
│   │ ---                                      │                   │
│   │ Attachments:                             │                   │
│   │ /path/to/file.pdf                        │                   │
│   └──────────────────────────────────────────┘                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: SEND (triggered by cron/systemd-timer/nmail watch)       │
│                                                                  │
│   nmail send [--dry-run] [--id <queue-id>]                       │
│       │                                                          │
│       ├─ Acquire queue lock (~/.local/state/nmail/queue-lock)    │
│       │                                                          │
│       ├─ For each file in queue/new/ (or specified --id):        │
│       │                                                          │
│       │   1. Move queue/new/<id> → queue/tmp/<id>                │
│       │                                                          │
│       │   2. nmail render queue/tmp/<id> → pipe to msmtp         │
│       │      │                                                   │
│       │      │  nmail render pipeline:                           │
│       │      │  ┌─────────────────────────────────┐             │
│       │      │  │ Parse headers                   │             │
│       │      │  │ Extract body (markdown)          │             │
│       │      │  │ Build multipart/alternative MIME │             │
│       │      │  │   text/plain  ← markdown as-is   │             │
│       │      │  │   text/html   ← markdown as-is   │             │
│       │      │  │ Attach files from Attachments:   │             │
│       │      │  │ Output RFC5322 to stdout         │             │
│       │      │  └─────────────────────────────────┘             │
│       │      │                                                   │
│       │      ▼                                                   │
│       │   msmtp -t < rendered_email                              │
│       │      │                                                   │
│       │      ├─ Success (exit 0):                                │
│       │      │   Move queue/tmp/<id> → sent/cur/<id>             │
│       │      │   Update X-nmail-Status: sent                     │
│       │      │   Log "mail:sent <id>"                            │
│       │      │   Fire hooks.d/on-sent <id>                       │
│       │      │                                                   │
│       │      └─ Failure (non-zero):                              │
│       │          Move queue/tmp/<id> → queue/cur/<id>            │
│       │          Update X-nmail-Status: failed                   │
│       │          Append X-nmail-Error: <msmtp stderr>            │
│       │          Log "mail:error <id> <reason>"                  │
│       │          Fire hooks.d/on-error <id> <reason>             │
│       │                                                          │
│       └─ Release queue lock                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Flow 2: Sync → Index → Search

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: SYNC                                                     │
│                                                                  │
│   nmail sync [--account <name>] [--dry-run]                      │
│       │                                                          │
│       ├─ Read config: which sync tool, which accounts            │
│       │                                                          │
│       ├─ Log "mail:sync-start"                                   │
│       │   Fire hooks.d/on-sync-start                             │
│       │                                                          │
│       ├─ For each configured account:                            │
│       │   ┌────────────────────────────────────────┐             │
│       │   │ mbsync <account>                        │             │
│       │   │   (or offlineimap, or imapfetch)        │             │
│       │   │                                          │             │
│       │   │ Output logged to logs/sync.log           │             │
│       │   └────────────────────────────────────────┘             │
│       │                                                          │
│       ├─ Count new messages in incoming/new/                     │
│       │                                                          │
│       ├─ Record sync timestamp:                                  │
│       │   date +%s > ~/.local/state/nmail/last-sync              │
│       │                                                          │
│       ├─ Log "mail:sync-end <new_count>"                         │
│       │   Fire hooks.d/on-sync-end <new_count>                   │
│       │                                                          │
│       └─ If new_count > 0:                                       │
│           Log "mail:new <count>"                                 │
│           Fire hooks.d/on-new <count>                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: INDEX (optional, uses notmuch)                            │
│                                                                  │
│   After sync, notmuch database needs refresh:                    │
│                                                                  │
│   notmuch new                                                    │
│       │                                                          │
│       └─ Indexes incoming/, sent/, archive/                      │
│                                                                  │
│   This can be triggered:                                         │
│   ├─ By hooks.d/on-sync-end calling notmuch new                  │
│   ├─ By nmail watch detecting new files in incoming/new/         │
│   └─ Manually via notmuch new                                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: SEARCH                                                   │
│                                                                  │
│   nmail search [--format ids|paths|summary] <query>              │
│       │                                                          │
│       ├─ With notmuch:                                           │
│       │   notmuch search --output=files <query>                  │
│       │                                                          │
│       ├─ Without notmuch (fallback):                             │
│       │   rg -l "<query>" ~/Mail/incoming/ ~/Mail/archive/       │
│       │       ~/Mail/sent/                                       │
│       │                                                          │
│       └─ Output: file paths (one per line)                       │
│                                                                  │
│   nmail open <id-or-path>                                        │
│       │                                                          │
│       ├─ Resolve ID to file path (via notmuch or glob)           │
│       │                                                          │
│       ├─ Mark as read (move incoming/new/ → incoming/cur/)       │
│       │                                                          │
│       └─ Open in $PAGER (less, bat, etc.)                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Flow 3: Event Loop (nmail watch)

```
┌──────────────────────────────────────────────────────────────────┐
│ nmail watch                                                      │
│                                                                  │
│   Watches Maildir with inotifywait:                              │
│                                                                  │
│   inotifywait -m -r \                                            │
│       -e create -e moved_to \                                    │
│       ~/Mail/incoming/new/ \                                     │
│       ~/Mail/queue/new/                                          │
│       │                                                          │
│       ├─ File appears in incoming/new/ →                          │
│       │   Log "mail:new 1"                                       │
│       │   Fire hooks.d/on-new 1                                  │
│       │                                                          │
│       └─ File appears in queue/new/ →                            │
│           Log "queue:new"                                        │
│           (Could trigger nmail send if configured)               │
│                                                                  │
│   Designed to run in background:                                 │
│   ├─ systemd --user service                                      │
│   ├─ tmux pane: nmail watch                                      │
│   └─ Manual: nmail watch &                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Flow 4: Reply/Forward

```
┌──────────────────────────────────────────────────────────────────┐
│ nmail reply <id>                                                 │
│       │                                                          │
│       ├─ Resolve <id> to message file in Maildir                 │
│       │                                                          │
│       ├─ Extract headers: From, To, Subject, Message-ID,         │
│       │   Date, References, In-Reply-To                          │
│       │                                                          │
│       ├─ Create reply draft:                                     │
│       │   ┌──────────────────────────────────────────┐           │
│       │   │ To: <original From>                       │           │
│       │   │ Cc:                                       │           │
│       │   │ Subject: Re: <original Subject>           │           │
│       │   │ In-Reply-To: <Message-ID>                 │           │
│       │   │ References: <accumulated>                 │           │
│       │   │                                           │           │
│       │   │ ---                                       │           │
│       │   │                                           │           │
│       │   │ On <date>, <from> wrote:                  │           │
│       │   │                                           │           │
│       │   │ > <quoted original>                       │           │
│       │   └──────────────────────────────────────────┘           │
│       │                                                          │
│       └─ Open in $EDITOR                                       │
│                                                                  │
│ nmail forward <id>                                               │
│       │                                                          │
│       ├─ Similar to reply, but:                                  │
│       │   - To: empty (user fills)                               │
│       │   - Subject: Fwd: <original Subject>                     │
│       │   - Include original as attachment (or inline quote)     │
│       │   - Copy original attachments to new draft               │
│       │                                                          │
│       └─ Open in $EDITOR                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```
