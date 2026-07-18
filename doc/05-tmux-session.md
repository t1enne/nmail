# tmux Session Bootstrap

## `nmail session` — the launcher

```bash
nmail session [--layout grid|windows] [--no-sync] [--no-watch]
```

Creates a productive mail environment in tmux. All panes run independent tools; tmux only orchestrates windows/panes.

## Behavior

1. Checks tmux is available
2. Attaches to existing session if one exists
3. Ensures Maildir directories exist
4. Runs `nmail sync` in background (unless `--no-sync`)
5. Starts `nmail watch` in background (unless `--no-watch`)
6. Creates tmux session with chosen layout
7. Attaches

## Grid Layout

```
┌─────────────────────┬──────────────────────┐
│ compose             │ inbox                │
│ (nvim ~/Mail/drafts)│ (lf ~/Mail/incoming) │
├─────────────────────┼──────────────────────┤
│ shell + logs        │ search               │
│ (tail -f mail.log,  │ (nmail search prompt) │
│  queue status)      │                      │
└─────────────────────┴──────────────────────┘
```

**Pane 0 (top-left):** `nvim` in `~/Mail/drafts/`
- Compose new: `:e new-draft.md`
- Edit existing: open draft file
- Save → `nmail compose` validates → queues

**Pane 1 (top-right):** `lf` in `~/Mail/incoming/`
- Navigate with j/k
- Enter to open in pager
- Space to toggle read/unread (via `nmail tag`)
- d to trash, a to archive

**Pane 2 (bottom-left):** shell + log tail
- Live `mail.log` output
- Queue status update on each event
- Run any `nmail` command manually

**Pane 3 (bottom-right):** search prompt
- Type: `nmail search tag:unread --interactive`
- fzf picker with message preview
- Enter to open selected

## Window Layout

```
1: compose  (nvim ~/Mail/drafts/)
2: inbox    (lf ~/Mail/incoming/)
3: search   (ready for nmail search)
4: contacts (less ~/.local/state/nmail/contacts.tsv)
5: queue    (lf ~/Mail/queue/new/)
6: logs     (tail -f ~/Mail/logs/mail.log)
7: sync     (nmail sync)
8: shell
```

## Options

```
--layout grid|windows   Layout style (default: grid)
--no-sync               Skip initial sync
--no-watch              Don't start file watcher
--project NAME          Tmux session name (default: "mail")
```

## Key Bindings (optional tmux.conf additions)

```bash
# ~/.tmux.conf additions for nmail

# Quick mail session launcher
bind M new-window -n mail "nmail session"
```

## systemd user service

```ini
# ~/.config/systemd/user/nmail-session.service
[Unit]
Description=nmail tmux session

[Service]
Type=forking
ExecStart=/usr/bin/tmux new-session -d -s mail -n compose 'nmail session'
ExecStop=/usr/bin/tmux kill-session -t mail
Restart=no

[Install]
WantedBy=default.target
```
