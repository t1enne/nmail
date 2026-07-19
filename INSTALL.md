# Installing nmail

nmail is a Python package. Install it with `uv`, `pip`, or from a GitHub clone. After installing the package, you must also configure **msmtp** (SMTP) and **mbsync** (IMAP) — nmail delegates all network operations to these tools.

---

## 1. System Dependencies

These are not Python packages. Install them with your OS package manager.

| Tool | Purpose | Package name |
|---|---|---|
| **msmtp** | SMTP relay — required to send mail | `msmtp` (Debian/Arch) or `msmtp` (brew) |
| **mbsync** | IMAP→Maildir sync — required to receive mail | `isync` (Debian), `isync` (Arch), or `isync` (brew) |
| **notmuch** | Fast full-text indexing and search | `notmuch` (recommended) |
| **bat** | Syntax-highlighted pager for reading mail | `bat` (recommended) |
| **fzf** | Interactive fuzzy finder for `nmail search --interactive` | `fzf` (recommended) |
| **ripgrep** | Fallback search when notmuch is unavailable | `ripgrep` (optional) |
| **inotify-tools** | Efficient Maildir watcher for `nmail watch` | `inotify-tools` (optional) |

### One-command install

```bash
# Debian / Ubuntu
sudo apt install -y msmtp isync notmuch bat fzf ripgrep inotify-tools

# Arch Linux
sudo pacman -S msmtp isync notmuch bat fzf ripgrep inotify-tools

# macOS (Homebrew)
brew install msmtp isync notmuch bat fzf ripgrep
```

### Verify

```bash
msmtp --version
mbsync --version
notmuch --version   # optional
```

---

## 2. Install the `nmail` Python Package

Python ≥3.11 required.

### Method A: uv tool install (recommended — global command)

```bash
# From PyPI (once published):
uv tool install nmail

# From the GitHub repository directly:
uv tool install git+https://github.com/nasrt/nmail

# From a local clone:
git clone https://github.com/nasrt/nmail
cd nmail
uv tool install .
```

After any of these, `nmail` is on your PATH:

```bash
nmail --help
```

To upgrade later:

```bash
uv tool upgrade nmail
# or, for git installs:
uv tool install --reinstall git+https://github.com/nasrt/nmail
```

### Method B: pip install

```bash
# From PyPI (once published):
pip install nmail

# From GitHub:
pip install git+https://github.com/nasrt/nmail

# From a local clone:
git clone https://github.com/nasrt/nmail
cd nmail
pip install .
```

### Method C: uv run (development / no install)

```bash
git clone https://github.com/nasrt/nmail
cd nmail
uv sync
uv run nmail --help
```

`uv sync` creates a virtualenv and installs all dependencies. Use `uv run nmail` instead of bare `nmail`. This is the right choice if you plan to edit the source.

### Method D: pipx

```bash
pipx install nmail
# or from git:
pipx install git+https://github.com/nasrt/nmail
```

pipx installs nmail into its own venv and adds the `nmail` command to your PATH — similar to `uv tool install`.

---

## 3. Verify the Install

```bash
# List all subcommands
nmail --help

# Check version and basic health
nmail status
```

On first run, nmail creates the default Maildir tree at `~/Mail/` and a default config at `~/.config/nmail/config.toml`.

---

## 4. Next: Configure

You need three config files before nmail can send and receive:

| File | Tool | Purpose |
|---|---|---|
| `~/.msmtprc` | msmtp | SMTP credentials for sending |
| `~/.mbsyncrc` | mbsync | IMAP credentials for receiving |
| `~/.config/nmail/config.toml` | nmail | nmail behaviour (optional — defaults work) |

See **[CONFIG.md](CONFIG.md)** for detailed setup of each file.

Quick verification after config:

```bash
# Test SMTP
echo "Subject: test" | msmtp -a personal you@example.com

# Test IMAP sync
mbsync personal

# Test end-to-end
nmail sync
nmail compose --to you@example.com --subject "E2E test"
nmail send
```

---

## 5. Shell Integration (optional)

### Auto-sync in background

Add to crontab (`crontab -e`):

```
*/5 * * * * nmail sync --quiet
```

Or run the persistent watcher:

```bash
nmail watch &   # monitors Maildir, fires hooks on new mail
```

### Shell aliases

```bash
alias nm='nmail'
alias nms='nmail search --interactive'
alias nmc='nmail compose'
alias nmsend='nmail send'
```
