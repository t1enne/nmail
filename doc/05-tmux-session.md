# tmux Session Bootstrap

## `mail-session` — the launcher

```bash
#!/usr/bin/env bash
# mail-session — launch nmail tmux workspace
#
# Creates a productive mail environment in tmux.
# All panes run independent tools; tmux only orchestrates windows/panes.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAIL_DIR="${MAIL_DIR:-$HOME/Mail}"
CONFIG="${NM_CONFIG:-$HOME/.config/nmail/config.toml}"
SESSION="${NM_SESSION:-mail}"

# Parse args
LAYOUT="grid"
NO_SYNC=false
NO_WATCH=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --layout)      LAYOUT="$2"; shift 2 ;;
        --layout=*)    LAYOUT="${1#*=}"; shift ;;
        --no-sync)     NO_SYNC=true; shift ;;
        --no-watch)    NO_WATCH=true; shift ;;
        --project)     SESSION="$2"; shift 2 ;;
        --project=*)   SESSION="${1#*=}"; shift ;;
        -h|--help)
            echo "Usage: mail-session [--layout grid|windows] [--no-sync] [--no-watch]"
            exit 0
            ;;
        *) shift ;;
    esac
done

# ---------------------------------------------------------------------------
# Check tmux
# ---------------------------------------------------------------------------

if ! command -v tmux &>/dev/null; then
    echo "mail-session: tmux not found" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Attach if session exists
# ---------------------------------------------------------------------------

if tmux has-session -t "$SESSION" 2>/dev/null; then
    exec tmux attach-session -t "$SESSION"
fi

# ---------------------------------------------------------------------------
# Ensure Maildir exists
# ---------------------------------------------------------------------------

mkdir -p \
    "$MAIL_DIR"/{incoming,archive,drafts,sent,trash,attachments,templates,queue,logs}/{cur,new,tmp} \
    "$HOME/.local/state/nmail"

# ---------------------------------------------------------------------------
# Initial sync (unless --no-sync)
# ---------------------------------------------------------------------------

if ! $NO_SYNC && command -v mail-sync &>/dev/null; then
    mail-sync &
fi

# ---------------------------------------------------------------------------
# Start watcher (unless --no-watch)
# ---------------------------------------------------------------------------

if ! $NO_WATCH && command -v mail-watch &>/dev/null; then
    mail-watch &
fi

# ---------------------------------------------------------------------------
# Grid Layout
# ---------------------------------------------------------------------------

if [[ "$LAYOUT" == "grid" ]]; then
    tmux new-session -d -s "$SESSION" -n "mail"

    # Pane 0: compose (nvim on drafts directory)
    tmux send-keys -t "$SESSION":0.0 \
        "cd '$MAIL_DIR/drafts' && ${EDITOR:-nvim} ." C-m

    # Pane 1: inbox (lf on incoming)
    tmux split-window -h -t "$SESSION":0.0
    tmux send-keys -t "$SESSION":0.1 \
        "cd '$MAIL_DIR/incoming' && ${NM_FILE_BROWSER:-lf}" C-m

    # Pane 2: shell + logs + queue status
    tmux split-window -v -t "$SESSION":0.0
    tmux send-keys -t "$SESSION":0.2 \
        "echo '=== nmail shell ==='; echo 'inbox: '; ls '$MAIL_DIR/incoming/new/' 2>/dev/null | wc -l | xargs echo '  new:'; ls '$MAIL_DIR/incoming/cur/' 2>/dev/null | wc -l | xargs echo '  read:'; echo 'queue: '; ls '$MAIL_DIR/queue/new/' 2>/dev/null | wc -l | xargs echo '  pending:'; echo; tail -f '$MAIL_DIR/logs/mail.log' 2>/dev/null || echo 'No log yet'" C-m

    # Pane 3: search (fzf prompt)
    tmux split-window -v -t "$SESSION":0.1
    tmux send-keys -t "$SESSION":0.3 \
        "echo 'mail-search — type query and press Enter'; echo '---'; if command -v notmuch &>/dev/null; then notmuch count; else echo 'notmuch not installed (grep fallback)'; fi; echo; exec bash" C-m

    # Set pane sizes
    tmux select-layout -t "$SESSION":0 tiled

    tmux attach-session -t "$SESSION"

# ---------------------------------------------------------------------------
# Window Layout
# ---------------------------------------------------------------------------

elif [[ "$LAYOUT" == "windows" ]]; then
    tmux new-session -d -s "$SESSION" -n "compose"
    tmux send-keys -t "$SESSION":compose \
        "cd '$MAIL_DIR/drafts' && ${EDITOR:-nvim} ." C-m

    tmux new-window -t "$SESSION" -n "inbox"
    tmux send-keys -t "$SESSION":inbox \
        "cd '$MAIL_DIR/incoming' && ${NM_FILE_BROWSER:-lf}" C-m

    tmux new-window -t "$SESSION" -n "search"
    tmux send-keys -t "$SESSION":search \
        "echo 'mail-search <query>'; exec bash" C-m

    tmux new-window -t "$SESSION" -n "contacts"
    tmux send-keys -t "$SESSION":contacts \
        "echo 'mail-contacts <query>'; exec bash" C-m

    tmux new-window -t "$SESSION" -n "queue"
    tmux send-keys -t "$SESSION":queue \
        "cd '$MAIL_DIR/queue/new' && ${NM_FILE_BROWSER:-lf}" C-m

    tmux new-window -t "$SESSION" -n "logs"
    tmux send-keys -t "$SESSION":logs \
        "tail -f '$MAIL_DIR/logs/mail.log' 2>/dev/null || echo 'No log yet; waiting...' && sleep 2 && tail -f '$MAIL_DIR/logs/mail.log'" C-m

    tmux new-window -t "$SESSION" -n "sync"
    tmux send-keys -t "$SESSION":sync \
        "echo 'mail-sync'; exec bash" C-m

    tmux new-window -t "$SESSION" -n "shell"
    tmux send-keys -t "$SESSION":shell \
        "echo 'nmail shell'; mail-status; exec bash" C-m

    # Start on compose window
    tmux select-window -t "$SESSION":compose

    tmux attach-session -t "$SESSION"

else
    echo "mail-session: unknown layout '$LAYOUT'. Use 'grid' or 'windows'." >&2
    exit 1
fi
```

## Key Bindings (optional tmux.conf additions)

```bash
# ~/.tmux.conf additions for nmail

# Quick mail session launcher
bind M new-window -n mail "mail-session"

# Within mail session:
# (these can be set in mail-session itself)

# C-m = compose new
# C-r = reply
# C-f = forward
# C-s = search
# C-n = next unread
# C-a = archive
# C-d = trash
# C-q = queue status
# C-l = toggle log pane
```

## Alternative: `mail-session` as a systemd user service

```ini
# ~/.config/systemd/user/mail-session.service
[Unit]
Description=nmail tmux session

[Service]
Type=forking
ExecStart=/usr/bin/tmux new-session -d -s mail -n compose 'mail-session'
ExecStop=/usr/bin/tmux kill-session -t mail
Restart=no
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```

## Session Workflow

```
$ mail-session
    │
    ├─ Creates tmux session "mail"
    │
    ├─ Pane 0 (top-left): nvim in ~/Mail/drafts/
    │   • Compose new: :e new-draft.md
    │   • Edit existing: open draft file
    │   • Save → mail-compose validates → queues
    │
    ├─ Pane 1 (top-right): lf in ~/Mail/incoming/
    │   • Navigate with j/k
    │   • Enter to open in pager
    │   • Space to toggle read/unread (via mail-tag)
    │   • d to trash, a to archive
    │
    ├─ Pane 2 (bottom-left): shell + log tail
    │   • Live mail.log output
    │   • Queue status update on each event
    │   • Run any mail-* command manually
    │
    └─ Pane 3 (bottom-right): search
        • Type: mail-search tag:unread --interactive
        • fzf picker with message preview
        • Enter to open selected
```
