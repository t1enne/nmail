# nmail — Problems & Usability Gaps

Found via manual exploratory testing of all CLI commands. Not exhaustive.

Legend: ✅ = fixed, ☐ = not yet fixed

---

## Crash / Stack Trace Bugs

### 1. ✅ `search tag:unread` crashes on stale notmuch entries

`nmail search tag:unread` crashed with `FileNotFoundError` when notmuch index referenced files no longer on disk. The default format rendered full message content and blew up on the first missing file.

**Fix applied:** `notmuch_search()` now filters `[r for r in results if Path(r).is_file()]` — stale index entries are silently dropped. Also `render_mail()` returns `""` for missing files as safety net.

---

### 2. ✅ `search --interactive` crashes without TTY

`nmail search --interactive` crashed with `OSError: [Errno 6] No such device or address: '/dev/tty'` when run outside a terminal.

**Fix applied:** Check `os.open("/dev/tty", ...)` before proceeding. On failure: print "interactive mode requires a terminal" to stderr and `raise SystemExit(1)`.

---

### 3. ✅ `open` crashes on stale notmuch entries

`nmail open reply-20260718-085225` crashed when notmuch returned a path that no longer exists.

**Fix applied:** `resolve_id()` now uses `.is_file()` everywhere (not `.exists()`), filtering out stale entries and directories.

---

### 4. ✅ `open` crashes with `IsADirectoryError`

A stale Maildir directory named like `reply-20260718-085225.md:2,S` was picked up by glob and passed to `path.read_text()`.

**Fix applied:** `resolve_id()` now only returns `.is_file()` paths. `mark_read()` also guards with `.is_file()`.

---

## Unfriendly / Misleading Output

### 5. ✅ `search` default output was raw dumped email body

Default was `--format preview` which rendered entire decoded message body. Unusable for browsing — hundreds of lines per message even with `--limit`.

**Fix applied:** Changed default format to `summary` — one line per message (`date  from  subject`). `--format preview` still available for explicit use.

---

### 6. ✅ `search` default output has no message count header

No indication of how many results matched.

**Fix applied:** Now prints `N results` or `N results (showing first M)` to stderr before results.

---

### 7. ✅ `search` empty result is silent

`nmail search from:nobody` printed nothing.

**Fix applied:** Prints "No results." to stderr.

---

### 8. ✅ `status` shows "0 new" when notmuch has 143 unread

`status` counted Maildir `new/` directories only. After initial sync moves everything to `cur/`, all messages appear "0 new" even when unread.

**Fix applied:** When notmuch is available, a 4th column `unread` is shown for the `incoming` folder via `notmuch count tag:unread`.

---

### 9. ☐ `search --format preview` renders raw base64 blobs

Some messages with base64-encoded MIME parts show decoded raw binary or quoted-printable garbage. Not a crash, but ugly.

**Future fix:** Decode all MIME transfer encodings in `_extract_body()` before rendering.

---

## Inconsistent Error Messages / UX

### 10. ✅ `archive` vs `trash` inconsistent error

`archive` said "requires at least one message ID", `trash` said "requires message IDs, --empty, or --age".

**Fix applied:** `archive` now says "requires at least one message ID or - for stdin".

---

### 11. ✅ `tag +test nonexistent` silently succeeds

`nmail tag +test junk` exited 0 with no output.

**Fix applied:** Now queries notmuch for each ID before tagging. Prints "ID not found: <id>" to stderr for non-existent IDs.

---

### 12. ☐ `tag` with no args prints generic Click error

"Missing argument 'OPERATION'" — not terrible but lacks usage hint. Low priority.

---

### 13. ✅ `contacts --update` has no progress feedback

`nmail contacts --update` scanned 2913 messages with zero output for 10+ seconds.

**Fix applied:** Now prints "Scanning mailbox for contacts..." and per-folder message counts as it goes.

---

## Design Gaps

### 14. ☐ `search` output (non-interactive) not pipe-friendly

`--format ids` output doesn't reliably pipe to `open`. The ID space is nothmuch-specific and some IDs (like `reply-20260718-085225`) resolve differently in `resolve_id()` than notmuch expects. Needs a consistent ID scheme across commands.

---

### 15. ✅ No `search --format summary`

Only full-body rendering or raw file paths were available. No one-line summary.

**Fix applied:** Added `summary` format. Also added `_print_summary()` helper with header-aware date/from/subject extraction. Default format changed to `summary`.

---

### 16. ☐ `bat` dependency not declared

`open` help says "Uses bat if available" but bat is not in pyproject.toml. Graceful fallback to `less` exists, but undocumented.

---

### 17. ☐ `drafts/` directory mixed: Maildir + raw `.md` files

Drafts include both Maildir structure (`cur/`, `new/`, `tmp/`) and bare `.md` files. Notmuch indexes the bare `.md` files and they leak into search results. When deleted, they leave stale index entries (mitigated by fix #1 but root cause remains).

**Fix:** Restructure drafts to live outside the notmuch-indexed tree, or store them as proper Maildir messages.

---

### 18. ☐ No `search --sort` option

Results always in notmuch default order. No `--sort=oldest-first` or `--sort=subject`.

---

### 19. ☐ No `search --offset` / pagination

`--limit N` works but no `--offset M` for next-page. Can't paginate.

---

### 20. ☐ Templates leak into search results

Notmuch indexes everything under `~/Mail/` including `templates/forward.md`. A `tag:unread` query returns template files even though they aren't mail messages.

**Fix:** Either add notmuch config to exclude `templates/` and `drafts/` folders, or filter them in `notmuch_search()`.

---

### 21. ☐ No `body:` search in help examples

Help shows `tag:`, `from:`, `subject:` but not `body:` — notmuch supports `body:` text search.

---

## Summary by Severity

| Severity | Count | Fixed | Remaining |
|----------|-------|-------|-----------|
| **Crash** | 4 | 4 | 0 |
| **Unfriendly** | 5 | 4 | 1 |
| **Inconsistent** | 4 | 3 | 1 |
| **Design gap** | 8 | 1 | 7 |

**Fixed: 12 of 21 issues**
