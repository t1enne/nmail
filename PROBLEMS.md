# nmail — Problems & Usability Gaps

Found via manual exploratory testing of all CLI commands. Not exhaustive.

---

## Crash / Stack Trace Bugs

### 1. `search tag:unread` crashes on stale notmuch entries

`nmail search tag:unread` crashes with `FileNotFoundError` when notmuch index references files that no longer exist (e.g. deleted drafts `reply-20260718-085225.md`). The default format renders full message content and blows up on the first missing file.

**Repro:**
```
nmail search tag:unread
```
→ `FileNotFoundError: [Errno 2] No such file or directory: '/home/nasrt/Mail/drafts/reply-20260718-085225.md'`

**Root cause:** Notmuch index is stale — files were deleted but `notmuch new` wasn't run (or doesn't catch these). nmail trusts notmuch output blindly instead of checking file existence before `render_mail()`.

**Fix:** Wrap `render_mail()` in try/except FileNotFoundError. Warn on stderr, skip missing. Also: run `notmuch new --no-hooks` as part of `nmail sync`.

---

### 2. `search --interactive` crashes without TTY

`nmail search --interactive tag:unread` crashes with `OSError: [Errno 6] No such device or address: '/dev/tty'` when run in a non-TTY context (e.g. scripted, piped, CI).

**Repro:**
```
nmail search --interactive tag:unread < /dev/null
```

**Fix:** Check if `/dev/tty` is available before `os.open("/dev/tty", ...)`. If unavailable: print helpful error "interactive mode requires a terminal" and exit 1 (not a stack trace).

---

### 3. `open` crashes on stale notmuch entries

`nmail open reply-20260718-085225` crashes with `FileNotFoundError` for the same stale-index reason as #1.

**Fix:** Same as #1 — check file existence, print "message not found: <id>" and exit 1.

---

### 4. `open` crashes on `reply-20260718-085225` with `IsADirectoryError`

A variant of the same file — `reply-20260718-085225.md` is gone, but `reply-20260718-085225.md:2,S` exists as a Maildir directory. `open` tries `path.read_text()` on a directory. Stack trace from `pathlib`.

**Fix:** Same as #1 — gate `render_mail()` on `path.is_file()`.

---

## Unfriendly / Misleading Output

### 5. `search tag:unread` output is raw dumped email body

No summary, no pager. Pipes entire raw message content to terminal. For 143 unread messages this is unusable. Even with `--limit 5`, output is hundreds of lines per message.

**Expected:** Default format should be a one-line-per-message summary (date, from, subject) like `notmuch search` output, or at minimum the format that `search --format preview` intends to provide (before it crashes on #1).

**Current defaults:** `--format preview` renders full raw message. The only usable format is `--format ids` or `--format files`, which show paths not summaries.

---

### 6. `search` default output has no message count header

`nmail search ""` dumps message bodies with no "Showing N of M results" header. User has no idea how many results exist.

**Fix:** Print `N results (showing first M)` or similar before first result when limit is applied.

---

### 7. `search` empty result is silent

`nmail search from:nobody` prints nothing. No "0 results" message. User can't tell search worked but found nothing vs. search failed.

**Fix:** Print "No results" to stderr when 0 matches.

---

### 8. `status` shows "0 new" when notmuch has 143 unread

`nmail status` reports `0 new` in incoming because all 2913 messages are in `cur/` not `new/`. But notmuch correctly knows 143 are tagged `unread`. Status counts maildir `new/` directories, which is misleading after initial sync moves everything to `cur/`.

**Fix:** Option A: also query notmuch for unread counts. Option B: rename the column to "new (maildir)" and add a notmuch-based "unread" column. At minimum, document the discrepancy.

---

### 9. `search --format preview` renders raw base64 blobs

The `--format preview` output for the Russian table email dumps raw base64-encoded MIME parts interspersed with quoted-printable HTML. No decoding.

**Fix:** Decode MIME content-transfer-encoding before rendering preview. Or at least strip raw base64 blocks and show `[base64-encoded content: N bytes]`.

---

## Inconsistent Error Messages / UX

### 10. `archive` says "requires at least one message ID" vs `trash` says "requires message IDs, --empty, or --age"

Same situation (no args), different phrasing. Inconsistent style.

**Fix:** Unify: `archive: requires message IDs or - for stdin` or `trash: requires at least one message ID, --empty, or --age`.

---

### 11. `tag +test nonexistent` silently succeeds (exit 0)

Tagging a nonexistent notmuch ID produces no output, exits 0. User can't tell the tag had no effect.

**Fix:** Warn "ID not found: nonexistent" to stderr. Exit 0 (not an error per se) but print feedback.

---

### 12. `tag` with no args prints Click's generic "Missing argument 'OPERATION'" — no usage hint

Generic Click error. Not terrible but could be friendlier: "Usage: nmail tag +tag|-tag ID..." inline rather than making user run `--help`.

---

### 13. `contacts` with no cache prints "Run with --update first" — but `--update` takes 10+ seconds with no progress

`nmail contacts --update` scans 2913 files. No progress bar, no "scanning N files..." message. Terminal sits silent.

**Fix:** Print "Scanning mailbox..." before starting. Show file count or spinner for large mailboxes.

---

## Design Gaps

### 14. `search` (non-interactive) is not pipe-friendly

Default format is full message body. `--format ids` returns notmuch IDs which are opaque (e.g. `reply-20260718-085225`). Can't pipe to `open` because `open` resolves these differently from notmuch. `search --format files` returns absolute paths — pipeable to `xargs nmail open` but file paths are ugly.

**Fix:** Make `--format ids` output valid input for `open`. Currently `nmail search --format ids tag:unread | head -1 | xargs nmail open` fails (#3). Ensure same ID space works across commands.

---

### 15. No `search --format summary`

There's no one-line-per-message summary format (date | from | subject | tags). The only non-crash output is full message rendering or raw file paths. `notmuch search` already provides this — nmail should wrap it.

**Fix:** Add `--format summary` that outputs `date from subject (tags)` like notmuch's default output.

---

### 16. `bat` dependency not declared

`nmail open` help says "Uses bat if available." But `bat` is not listed as dependency. Falls back silently to something else (presumably `less`). Graceful, but should be documented in README or pyproject.toml as optional.

---

### 17. `drafts/` directory mixed: Maildir structure + raw `.md` files

Maildir requires `cur/`, `new/`, `tmp/` subdirectories. But `drafts/` also has bare `.md` files alongside them. Notmuch indexes bare `.md` files as "mail" and includes them in search results. When these files are deleted/resolved, notmuch entries go stale.

**Fix:** Either keep drafts as pure markdown outside Maildir (e.g. `~/Mail/drafts-md/`) or store them as proper Maildir messages with markdown body. Mixing the two causes stale-index bugs.

---

### 18. No `search --sort` option

`nmail search` output is in notmuch default order (newest first? file order?). No way to sort by date ascending, subject, sender.

**Fix:** Pass `--sort=newest-first` or `--sort=oldest-first` to notmuch.

---

### 19. No `search --limit` with offset / pagination

`--limit N` gives first N results but no `--offset` for pagination. Can't do "next page."

**Fix:** Add `--offset M` to skip first M results.

---

### 20. `search` formats `files` returns draft template paths as results

Tag search `tag:unread` returns `/home/nasrt/Mail/templates/forward.md` — a template, not a mail message. Notmuch indexes templates because they're in the mail tree.

**Fix:** Exclude `templates/` and `drafts/` from notmuch index, or filter them out in nmail search results when displaying mail messages.

---

### 21. No `search body:<text>` in help examples

Help shows `tag:`, `from:`, `subject:` but not `body:` text search. Notmuch supports it. Missing from discoverability.

**Fix:** Add examples like `nmail search body:"meeting tomorrow"`.

---

## Summary by Severity

| Severity | Count | IDs |
|----------|-------|-----|
| **Crash** | 4 | #1, #2, #3, #4 |
| **Unfriendly** | 5 | #5, #6, #7, #8, #9 |
| **Inconsistent** | 4 | #10, #11, #12, #13 |
| **Design gap** | 8 | #14, #15, #16, #17, #18, #19, #20, #21 |

**Total: 21 issues**
