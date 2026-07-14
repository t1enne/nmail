# CLI Specification

## Conventions

- All commands exit 0 on success, non-zero on failure.
- Output is plain text, one record per line where applicable.
- All commands accept `--help` and `--version`.
- `MAIL_DIR` env var overrides `~/Mail` (default).
- `MAIL_CONFIG` env var overrides `~/.config/nmail/config.toml`.
- `NM_DRY_RUN=1` enables dry-run mode (commands log what they would do).

---

## mail-compose

```
mail-compose [options] [template-name|draft-file]

Create or edit a mail draft.

Arguments:
  template-name   Use ~/Mail/templates/<name>.md as starting point
  draft-file      Edit existing draft file directly

Options:
  --to ADDR         Pre-fill To: header
  --cc ADDR         Pre-fill Cc: header
  --bcc ADDR        Pre-fill Bcc: header
  --subject TEXT    Pre-fill Subject: header
  --attach FILE     Add attachment reference
  --no-send         Don't queue after editing; keep as draft only
  --queue           Queue immediately after saving (default)

If no arguments, creates ~/Mail/drafts/<timestamp>.md with default
template and opens in $EDITOR.

On $EDITOR exit:
  - Validates To: and Subject: present
  - If valid and --queue: moves to ~/Mail/queue/new/<id>
  - If valid and --no-send: stays in ~/Mail/drafts/
  - If invalid: warns, keeps file, exits 1

Exit codes:
  0   Draft queued successfully
  1   Draft invalid (missing headers)
  2   Draft saved but not queued (--no-send)
  3   Editor exited with error
```

---

## mail-render

```
mail-render [options] <input-file>

Convert a Markdown draft or queue file into RFC5322 MIME message.
Output to stdout.

Options:
  --format plain      Output only text/plain (no HTML, no MIME)
  --format mime       Output full multipart/alternative MIME (default)
  --format html       Output only text/html
  --attach DIR        Directory for resolving attachment paths
  --no-attachments    Skip attachment processing

The input file format:
  Header block (RFC822 style) until `---` separator
  Markdown body
  Optional `---` separator followed by attachment list

Attachments can be:
  - Absolute paths
  - Relative to ~/Mail/attachments/
  - Relative to draft file directory

Pipeline:
  1. Parse headers
  2. Extract Markdown body
  3. Convert to HTML via `pandoc -f markdown -t html`
  4. Build multipart/alternative MIME:
     - text/plain (Markdown as-is)
     - text/html (pandoc output)
  5. Encode attachments as base64 MIME parts
  6. Add Content-Type, MIME-Version, Date, Message-ID
  7. Output complete RFC5322 message

Exit codes:
  0   Rendered successfully
  1   Parse error
  2   pandoc not found (and HTML needed)
```

---

## mail-send

```
mail-send [options] [draft-file...]

Send queued messages via SMTP (msmtp).

Arguments:
  draft-file   Send specific draft/queue file(s) instead of draining queue

Options:
  --dry-run       Render but don't send
  --id ID         Send specific queue ID only
  --account NAME  Use specific SMTP account from config
  --retry N       Retry failed sends up to N times (default: 0)
  --all           Include queue/cur/ (previously failed) in addition to new/

Behavior:
  1. Acquires lock (~/.local/state/nmail/queue-lock)
  2. For each file in queue/new/ (or specified files):
     a. Moves to queue/tmp/
     b. Runs mail-render on it
     c. Pipes rendered output to `msmtp -t`
     d. On success: moves to sent/cur/
     e. On failure: moves to queue/cur/ with error annotation
  3. Releases lock

Exit codes:
  0   All sent successfully
  1   Some failed
  2   Queue empty
  3   Lock already held
```

---

## mail-sync

```
mail-sync [options]

Synchronize maildir with remote IMAP server(s).

Options:
  --account NAME   Sync only specific account
  --dry-run        Show what would be synced
  --full           Full sync (default is new-only with mbsync)
  --no-index       Skip notmuch re-index after sync

Behavior:
  1. Reads sync configuration from config.toml
  2. For each account, runs configured sync tool:
     mbsync <account>
     (or offlineimap, or custom command)
  3. Logs output to ~/Mail/logs/sync.log
  4. If notmuch configured: runs `notmuch new`
  5. Records timestamp to ~/.local/state/nmail/last-sync
  6. Fires hooks: sync-start, sync-end, mail:new (if new messages)

Exit codes:
  0   Sync completed successfully
  1   Sync error (partial)
  2   Sync tool not found
```

---

## mail-watch

```
mail-watch [options]

Watch Maildir for changes and fire events.

Options:
  --once        Run once and exit (check for new mail, fire events)
  --daemon      Run continuously (default)
  --no-hooks    Don't fire hook scripts

Behavior:
  Uses inotifywait to monitor:
    ~/Mail/incoming/new/   (new mail)
    ~/Mail/queue/new/      (new outbound)

  On event:
    Logs to ~/Mail/logs/mail.log
    Fires hooks.d/ scripts as appropriate

Exit codes:
  0   Normal exit (SIGTERM/SIGINT)
  1   inotifywait not available
```

---

## mail-open

```
mail-open <id|path>

Open a mail message in $PAGER.

Arguments:
  id     Numeric ID (resolved via notmuch or file listing)
  path   Direct path to Maildir file

Options:
  --headers-only   Show only headers
  --raw            Show raw RFC822 (no pager formatting)

Behavior:
  1. Resolve ID to file path:
     - `notmuch search --output=files id:<id>` if notmuch available
     - Glob ~/Mail/**/<id>* otherwise
  2. If in incoming/new/, move to incoming/cur/ (mark read)
  3. Open in $PAGER (with syntax highlighting via bat if available)
  4. With --raw: cat the raw file

Exit codes:
  0   Opened successfully
  1   Message not found
```

---

## mail-reply

```
mail-reply <id|path>

Create a reply draft from an existing message.

Arguments:
  id     Message ID to reply to
  path   Direct path to Maildir file

Options:
  --all           Reply to all recipients
  --template NAME Use specific template for reply
  --no-quote      Don't quote original message

Behavior:
  1. Resolve message
  2. Extract headers (From, To, Cc, Subject, Message-ID, References)
  3. Create draft with:
     - To: = original From (or From + Cc if --all)
     - Subject: = Re: <original>
     - In-Reply-To: <Message-ID>
     - References: <accumulated>
  4. If not --no-quote: quote original body with `> ` prefix
  5. Open in $EDITOR

Exit codes:
  0   Draft created
  1   Message not found
```

---

## mail-forward

```
mail-forward <id|path>

Create a forward draft from an existing message.

Arguments:
  id     Message ID to forward
  path   Direct path to Maildir file

Options:
  --inline        Quote original inline (default: attach original)
  --attach        Attach original as message/rfc822 (default)

Behavior:
  1. Resolve message
  2. Create draft with:
     - Subject: Fwd: <original>
     - Body includes original subject/from/date
  3. --attach: include original as attachment
  4. --inline: quote original body
  5. Open in $EDITOR

Exit codes:
  0   Draft created
  1   Message not found
```

---

## mail-search

```
mail-search [options] <query>

Search mail index. Uses notmuch if available, falls back to rg.

Arguments:
  query   Search terms (notmuch syntax: tag:unread, from:alice, etc.)

Options:
  --format ids       Output notmuch message IDs (default)
  --format paths     Output file paths
  --format summary   Output one-line summary per match
  --format json      Output JSON array of results
  --limit N          Max results (default: 100)
  --sort ORDER       newest-first (default), oldest-first
  --interactive      Open fzf picker with preview

Fallback (no notmuch):
  Uses rg to search raw Maildir files.
  Limited to text match; no tag:, from:, etc. support.
  Outputs file paths.

Interactive mode:
  mail-search --interactive <query>
    Opens fzf with preview pane showing rendered message.
    On selection: outputs selected file path.

Examples:
  mail-search tag:unread
  mail-search from:alice subject:invoice
  mail-search rust --interactive
  mail-search tag:todo --format paths
```

---

## mail-tag

```
mail-tag <operation> <tag> <id...>

Add or remove notmuch tags. Requires notmuch.

Operation:
  +<tag>   Add tag
  -<tag>   Remove tag

Arguments:
  tag    Tag name
  id...  One or more message IDs or file paths

Examples:
  mail-tag +todo 182
  mail-tag -unread 182 193 204
  mail-search tag:todo --format ids | mail-tag +reviewed -

Reads IDs from stdin if "-" is given as id argument:
  mail-tag +archived -
```

---

## mail-archive

```
mail-archive <id...>

Move message(s) from incoming/ to archive/cur/.

Arguments:
  id...  One or more message IDs or file paths
  -      Read IDs from stdin

Options:
  --tag TAG   Also add notmuch tag before archiving

Behavior:
  1. Resolve each ID to file path
  2. Move to ~/Mail/archive/cur/
  3. Log event

Exit codes:
  0   All archived
  1   Some not found
```

---

## mail-trash

```
mail-trash <id...>

Move message(s) to trash/cur/.

Arguments:
  id...  One or more message IDs or file paths
  -      Read IDs from stdin

Options:
  --force     Skip confirmation
  --empty     Permanently delete trash contents
  --age DAYS  Delete trash older than DAYS

Behavior (--empty):
  Removes all files in ~/Mail/trash/cur/
  Prompts for confirmation unless --force

Behavior (--age DAYS):
  Finds trash files older than DAYS and removes them
  Reports count of deleted messages

Exit codes:
  0   Moved to trash / emptied
  1   Some not found
```

---

## mail-contacts

```
mail-contacts [options] [query]

Manage and search contacts extracted from mail.

Options:
  --update        Rebuild contact cache from all mail
  --format tsv    Tab-separated (default)
  --format json   JSON output

Without --update:
  Searches ~/.local/state/nmail/contacts.tsv for query
  Output: name, email, count (tab-separated)

With --update:
  Scans From:, To:, Cc: headers in all mail
  Extracts names and email addresses
  Counts occurrences
  Writes to ~/.local/state/nmail/contacts.tsv

Examples:
  mail-contacts alice              # find contacts matching "alice"
  mail-contacts --update           # rebuild cache
  mail-contacts | fzf | cut -f2    # interactive contact picker
```

---

## mail-template

```
mail-template <operation> [name]

Manage compose templates.

Operation:
  list           List available templates
  show NAME      Display template contents
  edit NAME      Edit template in $EDITOR
  create NAME    Create new template from stdin or $EDITOR
  delete NAME    Remove template

Templates stored in ~/Mail/templates/*.md

Built-in templates:
  default.md     Empty headers with signature
  reply.md       Reply headers with quote placeholder
  forward.md     Forward headers

Examples:
  mail-template list
  mail-template show default
  mail-template create meeting
```

---

## mail-status

```
mail-status [options]

Show mailbox status overview.

Options:
  --json      Output JSON
  --watch     Continuous refresh (every N seconds)

Output:
  Incoming:   N new, M total
  Archive:    N total
  Sent:       N total
  Drafts:     N pending
  Queue:      N pending, M failed
  Trash:      N total
  Last sync:  timestamp or "never"

Exit codes:
  0   OK
```

---

## mail-log

```
mail-log [options]

Query the structured activity log.

Options:
  --follow     Tail the log (like tail -f)
  --since TIME Filter entries since TIME (ISO 8601 or relative: 1h, 2d)
  --level N    Minimum log level: 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR
  --event TYPE Filter by event type: sync, send, error, new, draft, trash
  --json       Output JSON lines

Log format (one JSON line per event):
  {"ts":"2026-07-13T14:30:00Z","event":"mail:new","count":3}

Examples:
  mail-log --follow
  mail-log --since 2h --level 2
  mail-log --event error
```

---

## mail-attach

```
mail-attach <operation> [args]

Manage the attachment directory.

Operation:
  list           List saved attachments
  save ID PATH   Extract attachment from message, save to PATH
  open ID N      Open N-th attachment from message
  clean          Remove orphaned attachments

Attachments are stored in ~/Mail/attachments/<msg-id>/

Examples:
  mail-attach list
  mail-attach save 182 ./invoice.pdf
  mail-attach open 182 1
```

---

## mail-hook

```
mail-hook <event> [args...]

Manually trigger hook scripts.

Arguments:
  event   Event name: new, sent, error, sync-start, sync-end, draft, trash
  args    Arguments passed to hook scripts

Behavior:
  Runs all executables in ~/.config/nmail/hooks.d/ matching <event>
  Each gets event name + args as positional parameters

Examples:
  mail-hook new 3
  mail-hook sent queue-abc123
  mail-hook error queue-abc123 "SMTP timeout"
```

---

## mail-session

```
mail-session [options]

Launch tmux workspace for nmail.

Options:
  --layout grid      4-pane grid layout (default)
  --layout windows   Separate tmux windows per function
  --no-sync          Don't run mail-sync on launch
  --no-watch         Don't start mail-watch
  --project NAME     Tmux session name (default: "mail")

Behavior:
  Creates a tmux session with:
    Grid layout:
      ┌──────────┬──────────┐
      │ compose  │ inbox    │
      │ (nvim)   │ (lf)     │
      ├──────────┼──────────┤
      │ shell    │ search   │
      │ queue    │ (fzf)    │
      │ logs     │          │
      └──────────┴──────────┘

    Window layout:
      1: compose  (nvim ~/Mail/drafts/)
      2: inbox    (lf ~/Mail/incoming/)
      3: search   (ready for mail-search)
      4: contacts (less ~/.local/state/nmail/contacts.tsv)
      5: queue    (lf ~/Mail/queue/new/)
      6: logs     (tail -f ~/Mail/logs/mail.log)
      7: sync     (mail-sync)
      8: shell

  Attaches to existing session if one exists with same name.

Exit codes:
  0   Launched or attached
  1   tmux not found
```

---

## Common Options

All commands share these:

```
--help           Show help and exit
--version        Show version and exit
--config PATH    Use alternate config file
--maildir PATH   Use alternate mail directory
--dry-run        Show what would be done, don't do it
--verbose        More output
--quiet          Less output
```
