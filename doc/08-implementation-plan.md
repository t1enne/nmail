# Staged Implementation Plan

## Phase 0: Foundation (MVP) — Weeks 1-2

**Goal:** Compose, queue, send. Filesystem-only. No search, no sync, no tmux.

### Deliverables

```
bin/
├── mail-compose        # Create draft, validate, queue
├── mail-render         # Markdown → MIME (text/plain + text/html)
├── mail-send           # Drain queue → msmtp
├── mail-open           # Open message in pager
├── mail-status         # Quick counts
└── mail-log            # Read/write structured log

src/
├── common.sh           # Shared: config reading, logging, Maildir ops
├── render.sh           # Parse draft, convert markdown, build MIME
└── maildir.sh          # Maildir helpers (move, flag, resolve)

config/
└── config.toml         # Default config

templates/
├── default.md
├── reply.md
└── forward.md

install.sh              # Symlink bin/ → ~/.local/bin/, init ~/Mail/
```

### What works end of Phase 0

```bash
# Compose mail
mail-compose
# → nvim opens, user writes draft, saves, exits
# → draft validated, moved to queue/new/

# Send queue
mail-send
# → renders to MIME, pipes to msmtp, moves to sent/

# Open a message
mail-open 182
# → resolves ID, opens in bat/less

# Check status
mail-status
# → Incoming: 0 new, 12 total
#   Queue: 1 pending, 0 failed
#   Sent: 45 total
```

### Key decisions for Phase 0
- Shell scripts only (bash). No Rust/Go/Python dependency yet.
- `mail-render` uses pandoc for markdown→HTML. Graceful fallback to plain text.
- `msmtp` must be installed and configured separately.
- Maildir structure is created by `install.sh`.

---

## Phase 1: Sync + Search — Weeks 3-4

**Goal:** Receive mail, index, search. Integrate external tools.

### New Commands

```
bin/
├── mail-sync           # Wrap mbsync/offlineimap
├── mail-search         # notmuch + rg fallback
├── mail-watch          # inotifywait-based event watcher
├── mail-reply          # Create reply draft
├── mail-forward        # Create forward draft
├── mail-tag            # notmuch tag management
├── mail-archive        # Move to archive
├── mail-trash          # Move to trash / empty
└── mail-contacts       # Extract contacts from headers

src/
└── notmuch.sh          # notmuch wrappers with graceful fallback
```

### What works end of Phase 1

```bash
# Sync mail
mail-sync
# → mbsync fetches, notmuch indexes, hooks fire

# Search
mail-search tag:unread from:alice
# notmuch search → file paths

# Open with fzf
mail-search --interactive tag:unread
# fzf preview → select → open

# Reply
mail-reply 182
# extracts headers, creates draft with quote, opens nvim

# Tag pipeline
mail-search --format ids from:bob | mail-tag +bob -

# Archive
mail-search --format ids tag:done | mail-archive -

# Watch for new mail
mail-watch &
# inotifywait on incoming/new/ → log + hooks
```

---

## Phase 2: tmux Workspace — Weeks 5-6

**Goal:** Productive terminal workspace. Composability demonstrations.

### New Commands

```
bin/
└── mail-session        # tmux bootstrap

config/
└── hooks.d/            # Example hook scripts
    ├── on-new
    ├── on-sent
    └── on-error
```

### What works end of Phase 2

```bash
mail-session
# → tmux session with 4 panes:
#   compose (nvim) | inbox (lf)
#   shell+log       | search (fzf)

mail-session --layout windows
# → 8 tmux windows
```

### Composable pipelines work:

```bash
mail-search tag:unread | fzf | mail-open
mail-contacts alice | fzf | xargs mail-compose --to
mail-search tag:todo | mail-archive -
mail-log --since 1h --event error
```

---

## Phase 3: Polish + Plugins — Weeks 7-8

**Goal:** Hook/plugin system, templates, attachments, configuration polish.

### New Commands

```
bin/
├── mail-template       # Manage templates
├── mail-attach         # Manage attachment directory
├── mail-hook           # Hook dispatcher (used internally)
└── mail-plugin         # Plugin manager (optional)
```

### What works end of Phase 3

```bash
# Templates
mail-template list
mail-template create meeting
mail-compose meeting

# Attachments
mail-attach list 182
mail-attach save 182 ./file.pdf

# Hooks fire automatically
# on-new: notify-send, re-index notmuch
# on-error: notify-send critical, retry queue
# on-sync-end: stats update

# Plugins
mail-plugin install ~/dev/nmail-plugin-gpg
mail-plugin list
```

---

## Phase 4: Advanced Features — Ongoing

**Goal:** What the community builds on top.

### Ideas (not spec'd yet)

- GPG signing/encryption plugin
- HTML email rendering (w3m/lynx → plain text fallback)
- Thread-aware operations (reply to thread, archive thread)
- Address book integration (khard, CardDAV)
- Calendar integration (event invites → khal)
- Multiple account profiles
- Mail merge (template + CSV → batch send)
- Spam learning (bogofilter/rspamd integration)
- Offline mode (full local operations, sync when connected)
- Stats dashboard (mail-log --stats → terminal charts)
- Mutt/neomutt compatibility layer (use nmail commands as mutt backend)
- GitHub notifications → mail bridge
- RSS → mail bridge

---

## Dependency Map

```
Phase 0: bash, coreutils, msmtp, pandoc (optional: bat, nvim)
Phase 1: + mbsync, notmuch, inotify-tools, fzf, ripgrep
Phase 2: + tmux, lf, notify-send
Phase 3: + jq (for JSON log queries)
Phase 4: + community-driven
```

## Success Criteria per Phase

### Phase 0 (MVP)
- [ ] `mail-compose` opens editor, saves to queue
- [ ] `mail-render` produces valid MIME from markdown
- [ ] `mail-send` drains queue through msmtp successfully
- [ ] `mail-open` displays message in pager
- [ ] `mail-status` shows correct counts
- [ ] All commands work standalone (no tmux needed)
- [ ] `install.sh` sets up full directory structure

### Phase 1
- [ ] `mail-sync` fetches mail via mbsync
- [ ] `mail-search` returns results (notmuch or rg fallback)
- [ ] `mail-reply` creates correct reply draft
- [ ] `mail-forward` creates correct forward draft
- [ ] `mail-archive`/`mail-trash` move messages correctly
- [ ] `mail-tag` integrates with notmuch
- [ ] `mail-watch` detects new mail and fires events

### Phase 2
- [ ] `mail-session` creates tmux workspace
- [ ] Grid layout: 4 panes functional
- [ ] Window layout: 8 windows functional
- [ ] Shell pipelines demonstrated and documented

### Phase 3
- [ ] Hook system fires on all events
- [ ] Templates work end-to-end
- [ ] Attachments save/open correctly
- [ ] Plugin manifest format validated

---

## File Size Budget (per script)

Target each script at 50-200 lines. Core libraries can be larger.

```
mail-compose      ~100 lines
mail-render       ~150 lines
mail-send         ~100 lines
mail-sync         ~80 lines
mail-search       ~120 lines (includes notmuch + rg paths)
mail-open         ~60 lines
mail-reply        ~100 lines
mail-forward      ~80 lines
mail-tag          ~40 lines
mail-archive      ~30 lines
mail-trash        ~50 lines
mail-status       ~80 lines
mail-log          ~60 lines
mail-watch        ~40 lines
mail-contacts     ~80 lines
mail-attach       ~60 lines
mail-template     ~60 lines
mail-hook         ~40 lines
mail-session      ~120 lines
mail-plugin       ~100 lines

common.sh         ~200 lines
render.sh         ~150 lines
maildir.sh        ~100 lines
notmuch.sh        ~80 lines
```

Total: ~1,800 lines of documented, tested shell script.
