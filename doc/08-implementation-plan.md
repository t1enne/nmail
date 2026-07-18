# Staged Implementation Plan

## Phase 0: Foundation (MVP) — Done

**Goal:** Compose, render, send. Filesystem-only.

### Delivered

```
src/nmail/
├── cli.py                # Click entrypoint
├── cli_commands1.py      # compose, forward, open, render, reply, search, send, status, sync
├── cli_commands2.py      # archive, attach, contacts, hook, log, session, tag, template, trash, watch
├── config.py             # TOML config loader
├── constants.py          # Shared constants
├── drafts.py             # Draft parsing (MD + headers)
├── headers.py            # Header extraction
├── logging.py            # Structured log
├── maildir.py            # Maildir operations
├── notmuch.py            # notmuch wrapper
├── render.py             # Markdown → RFC5322 MIME
└── shared.py             # Shared helpers

pyproject.toml            # Python project config
Makefile                  # format, lint, typecheck
```

### What works

```bash
# Compose mail
nmail compose
# → nvim opens, user writes draft, saves, exits
# → draft validated, moved to queue/new/

# Render preview
nmail render ~/Mail/drafts/draft.md

# Send queue
nmail send
# → renders to MIME, pipes to msmtp, moves to sent/

# Open a message
nmail open 182
# → resolves ID, opens in bat/less

# Check status
nmail status
# → Incoming: 0 new, 12 total
#   Queue: 1 pending, 0 failed
#   Sent: 45 total

# Search
nmail search tag:unread from:alice

# Reply
nmail reply 182
```

---

## Phase 1: Sync + Search — Planned

**Goal:** Receive mail, index, search. Integrate external tools.

### Commands

- `nmail sync` — fetch via mbsync
- `nmail search` — notmuch + rg fallback
- `nmail watch` — inotifywait-based watcher
- `nmail reply` — create reply draft
- `nmail forward` — create forward draft
- `nmail tag` — notmuch tag management
- `nmail archive` — move to archive
- `nmail trash` — move to trash / empty
- `nmail contacts` — extract contacts from headers

### What works end of Phase 1

```bash
# Sync mail
nmail sync
# → mbsync fetches, notmuch indexes, hooks fire

# Search
nmail search tag:unread from:alice
# notmuch search → file paths

# Open with fzf
nmail search --interactive tag:unread
# fzf preview → select → open

# Reply
nmail reply 182
# extracts headers, creates draft with quote, opens nvim

# Tag pipeline
nmail search --format ids from:bob | nmail tag +bob -

# Archive
nmail search --format ids tag:done | nmail archive -

# Watch for new mail
nmail watch &
# inotifywait on incoming/new/ → log + hooks
```

---

## Phase 2: tmux Workspace — Planned

**Goal:** Productive terminal workspace.

### Commands

- `nmail session` — tmux bootstrap

### What works end of Phase 2

```bash
nmail session
# → tmux session with 4 panes:
#   compose (nvim) | inbox (lf)
#   shell+log       | search (fzf)

nmail session --layout windows
# → 8 tmux windows
```

### Composable pipelines work:

```bash
nmail search tag:unread | fzf | nmail open
nmail contacts alice | fzf | xargs nmail compose --to
nmail search tag:todo | nmail archive -
nmail log --since 1h --event error
```

---

## Phase 3: Polish + Plugins — Planned

**Goal:** Hook/plugin system, templates, attachments.

### Commands

- `nmail template` — manage templates
- `nmail attach` — manage attachment directory
- `nmail hook` — hook dispatcher
- `nmail plugin` — plugin manager

### What works end of Phase 3

```bash
# Templates
nmail template list
nmail template create meeting
nmail compose meeting

# Attachments
nmail attach list 182
nmail attach save 182 ./file.pdf

# Hooks fire automatically
# on-new: notify-send, re-index notmuch
# on-error: notify-send critical, retry queue

# Plugins
nmail plugin install ~/dev/nmail-plugin-gpg
nmail plugin list
```

---

## Phase 4: Advanced Features — Ongoing

**Goal:** What the community builds on top.

### Ideas

- GPG signing/encryption plugin
- HTML email rendering (w3m/lynx → plain text fallback)
- Thread-aware operations (reply to thread, archive thread)
- Address book integration (khard, CardDAV)
- Calendar integration (event invites → khal)
- Multiple account profiles
- Mail merge (template + CSV → batch send)
- Spam learning (bogofilter/rspamd integration)
- Offline mode (full local operations, sync when connected)
- Stats dashboard
- Mutt/neomutt compatibility layer
- GitHub notifications → mail bridge
- RSS → mail bridge

---

## Dependency Map

```
Phase 0: Python ≥3.11, click, msmtp (optional: bat, nvim)
Phase 1: + mbsync, notmuch, inotify-tools, fzf, ripgrep
Phase 2: + tmux, lf
Phase 3: + jq
Phase 4: + community-driven
```

## Success Criteria per Phase

### Phase 0 (MVP) — Done
- [x] `nmail compose` opens editor, saves to queue
- [x] `nmail render` produces valid MIME from markdown
- [x] `nmail send` drains queue through msmtp successfully
- [x] `nmail open` displays message in pager
- [x] `nmail status` shows correct counts
- [x] All commands work standalone (no tmux needed)

### Phase 1
- [ ] `nmail sync` fetches mail via mbsync
- [ ] `nmail search` returns results (notmuch or rg fallback)
- [ ] `nmail reply` creates correct reply draft
- [ ] `nmail forward` creates correct forward draft
- [ ] `nmail archive`/`nmail trash` move messages correctly
- [ ] `nmail tag` integrates with notmuch
- [ ] `nmail watch` detects new mail and fires events

### Phase 2
- [ ] `nmail session` creates tmux workspace
- [ ] Grid layout: 4 panes functional
- [ ] Window layout: 8 windows functional
- [ ] Shell pipelines demonstrated and documented

### Phase 3
- [ ] Hook system fires on all events
- [ ] Templates work end-to-end
- [ ] Attachments save/open correctly
- [ ] Plugin manifest format validated

## Code Structure

```
src/nmail/                # Python package (~13 modules)
├── cli.py                # Entrypoint + subcommand registration
├── cli_commands1.py      # Half the subcommands
├── cli_commands2.py      # Other half
├── config.py             # TOML → dict
├── constants.py          # Paths, defaults
├── drafts.py             # Draft parse/validate
├── headers.py            # Header extraction
├── logging.py            # Structured JSON log
├── maildir.py            # Maildir ops
├── notmuch.py            # notmuch wrapper
├── render.py             # Markdown → RFC5322 MIME
└── shared.py             # Editor, pager, file helpers
```
