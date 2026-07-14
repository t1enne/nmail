# nmail Architecture

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER                                       │
│  shell pipeline, keybind, or mail-session tmux bootstrap            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────────┐
│  mail-compose │     │  mail-search  │     │   mail-sync       │
│  mail-reply   │     │  mail-tag     │     │   mail-watch      │
│  mail-forward │     │  mail-open    │     │   mail-fetch      │
│  mail-send    │     │  mail-archive │     └─────────┬─────────┘
│  mail-render  │     │  mail-trash   │               │
└───────┬───────┘     └───────┬───────┘               │
        │                     │                       │
        ▼                     ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FILESYSTEM LAYER                               │
│                                                                     │
│  ~/Mail/                                                            │
│  ├── incoming/new/     ← new mail (Maildir)                         │
│  ├── incoming/cur/     ← read mail                                  │
│  ├── archive/cur/      ← archived mail (Maildir++)                  │
│  ├── drafts/*.md       ← Markdown drafts                            │
│  ├── sent/cur/         ← sent mail                                  │
│  ├── trash/cur/        ← deleted mail                               │
│  ├── attachments/      ← saved attachments                          │
│  ├── templates/*.md    ← compose templates                          │
│  ├── queue/new/        ← outbound queue (Maildir)                   │
│  ├── queue/cur/        ← processed queue                            │
│  ├── queue/tmp/        ← in-progress                                │
│  └── logs/mail.log     ← structured log                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────────┐
│   INDEX       │     │   TRANSPORT   │     │    RENDER         │
│               │     │               │     │                   │
│  notmuch      │     │  mbsync       │     │  mail-render      │
│  (optional)   │     │  msmtp        │     │  (markdown→MIME)  │
│               │     │  offlineimap  │     │                   │
└───────────────┘     └───────────────┘     └───────────────────┘
```

## Design Principles

1. **Filesystem is the API.** Every tool reads/writes files. No daemon, no socket, no shared memory. Tools compose via the shell.

2. **Maildir everywhere.** Incoming, sent, archive, trash, queue—all Maildir layout. `tmp/`, `new/`, `cur/` with `:2,` flags suffix. Standard tools (mbsync, notmuch, mu) work natively.

3. **Drafts are Markdown.** Human-editable. Headers in YAML-style frontmatter or RFC822-style header block above `---`. Body is Markdown. `mail-render` produces RFC5322+MIME.

4. **Queue-based sending.** `mail-compose` writes to `queue/new/`. A background sender (cron, systemd timer, or `mail-watch`) drains the queue through `msmtp` into `sent/`. Non-blocking.

5. **Tmux is workspace, not application.** `mail-session` is a shell script that creates a tmux session with panes running NeoVim, lf/yazi, `tail -f` on logs. No custom TUI.

6. **Event-driven via filesystem.** `inotifywait` on Maildir directories triggers hooks. New mail → notification → refresh. Queue drained → log event.

7. **Plain-text configuration.** Single TOML file. No DSL, no database.

8. **Optional integrations.** notmuch for search, mbsync for IMAP, msmtp for SMTP, pandoc for rendering. Each is optional. Fall back to `grep`/`fd` for search when notmuch absent.

## Component Map

```
                    ┌──────────────────────────┐
                    │      mail-session         │
                    │   (tmux bootstrap)        │
                    └──────────┬───────────────┘
                               │ orchestrates panes
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ compose  │   │  inbox   │   │  search  │
        │ (nvim)   │   │ (lf)     │   │ (fzf)    │
        └──────────┘   └──────────┘   └──────────┘
                │              │              │
                ▼              ▼              ▼
        ┌──────────────────────────────────────────┐
        │           STANDALONE COMMANDS            │
        │  mail-compose, mail-open, mail-search,   │
        │  mail-render, mail-send, mail-sync,      │
        │  mail-tag, mail-archive, mail-trash,     │
        │  mail-reply, mail-forward, mail-status,  │
        │  mail-contacts, mail-template, mail-log  │
        └──────────────────────────────────────────┘
                │              │              │
                ▼              ▼              ▼
        ┌──────────────────────────────────────────┐
        │              FILESYSTEM                   │
        │              ~/Mail/                      │
        └──────────────────────────────────────────┘
```

## Data Flow: Compose → Queue → Send

```
  User                 mail-compose               Queue                 mail-send              SMTP
  ────                 ────────────               ─────                 ─────────              ────
    │                       │                       │                       │                    │
    │  edit draft.md        │                       │                       │                    │
    │──────────────────────►│                       │                       │                    │
    │                       │                       │                       │                    │
    │                       │  write to              │                       │                    │
    │                       │  queue/new/            │                       │                    │
    │                       │──────────────────────►│                       │                    │
    │                       │                       │                       │                    │
    │                       │                       │  cron/systemd timer    │                    │
    │                       │                       │  triggers mail-send    │                    │
    │                       │                       │──────────────────────►│                    │
    │                       │                       │                       │                    │
    │                       │                       │                       │  mail-render       │
    │                       │                       │                       │  markdown→MIME     │
    │                       │                       │                       │────────┐           │
    │                       │                       │                       │        │           │
    │                       │                       │                       │◄───────┘           │
    │                       │                       │                       │                    │
    │                       │                       │                       │  msmtp send        │
    │                       │                       │                       │───────────────────►│
    │                       │                       │                       │                    │
    │                       │                       │                       │  move to sent/     │
    │                       │                       │                       │────────┐           │
    │                       │                       │                       │        │           │
    │                       │                       │                       │◄───────┘           │
    │                       │                       │                       │                    │
    │                       │                       │  log event            │                    │
    │                       │                       │◄──────────────────────│                    │
    │                       │                       │                       │                    │
```

## Data Flow: Sync → Index → Search

```
  Remote (IMAP)         mail-sync              Maildir              notmuch              mail-search
  ─────────────         ─────────              ───────              ───────              ───────────
       │                     │                     │                     │                     │
       │  fetch new mail     │                     │                     │                     │
       │◄───────────────────►│                     │                     │                     │
       │  via mbsync         │                     │                     │                     │
       │                     │                     │                     │                     │
       │                     │  write to           │                     │                     │
       │                     │  incoming/new/      │                     │                     │
       │                     │────────────────────►│                     │                     │
       │                     │                     │                     │                     │
       │                     │  fire hook:         │                     │                     │
       │                     │  mail:new           │                     │                     │
       │                     │────────┐            │                     │                     │
       │                     │        │            │                     │                     │
       │                     │◄───────┘            │                     │                     │
       │                     │                     │                     │                     │
       │                     │                     │  notmuch new        │                     │
       │                     │                     │────────────────────►│                     │
       │                     │                     │                     │                     │
       │                     │                     │                     │  index messages      │
       │                     │                     │                     │────────┐            │
       │                     │                     │                     │        │            │
       │                     │                     │                     │◄───────┘            │
       │                     │                     │                     │                     │
       │                     │                     │                     │                     │
       │                     │                     │                     │                     │  user query
       │                     │                     │                     │                     │◄────
       │                     │                     │                     │                     │
       │                     │                     │                     │  notmuch search     │
       │                     │                     │                     │────────────────────►│
       │                     │                     │                     │  result IDs         │
       │                     │                     │                     │                     │
       │                     │                     │                     │                     │  resolve IDs
       │                     │                     │                     │                     │  to file paths
       │                     │                     │                     │                     │────────┐
       │                     │                     │                     │                     │        │
       │                     │                     │                     │                     │◄───────┘
       │                     │                     │                     │                     │
       │                     │                     │                     │                     │  output paths
       │                     │                     │                     │                     │────────┐
       │                     │                     │                     │                     │        │
       │                     │                     │                     │                     │◄───────┘
       │                     │                     │                     │                     │
```

## Hook Architecture

```
── Operation ──► mail-<command> ──► ~/Mail/logs/mail.log
                       │
                       ▼
              ~/.config/nmail/hooks.d/
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
         on-new     on-sent   on-error
         .sh        .sh       .sh
              │        │        │
              ▼        ▼        ▼
         notify-send  move to  retry
                      sent/    logic
```

Hooks are executables in `~/.config/nmail/hooks.d/`. Each receives event name + payload as args. Non-zero exit = failure but doesn't abort. Events:

- `mail:new <count>` — new messages arrived
- `mail:sent <queue-id>` — message sent successfully
- `mail:error <queue-id> <error>` — send failed
- `mail:sync-start` / `mail:sync-end` — sync lifecycle
- `mail:draft <path>` — draft saved
- `mail:trash <path>` — message moved to trash
