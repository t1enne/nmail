# Composability: Example Shell Pipelines

## Philosophy

Every `nmail` subcommand is a Unix filter. Input from stdin/files, output to stdout/files.
Compose with pipes, xargs, fzf, jq, etc. No monolithic client needed.

---

## Reading Mail

```bash
# Open most recent 10 messages, pick one with fzf
nmail search --format paths tag:unread --limit 50 \
  | while read f; do echo "$(head -50 "$f" | grep '^Subject:' | head -1)  $f"; done \
  | fzf --preview 'bat --language=email {2}' \
  | awk '{print $NF}' \
  | xargs nmail open

# Open oldest unread
nmail search --format paths --sort oldest-first tag:unread --limit 1 \
  | xargs nmail open

# Count unread
nmail status --json | jq '.incoming.new'
```

---

## Composing

```bash
# Compose new mail to Alice
nmail compose --to alice@example.com --subject "Meeting notes"

# Compose from template
nmail compose meeting --to team@example.com

# Compose and queue immediately (non-interactive)
echo -e "To: bob@example.com\nSubject: Test\n\n---\n\nHello." \
  | nmail compose --stdin

# Batch compose from file list
while read to subject; do
  nmail compose --to "$to" --subject "$subject"
done < recipients.txt
```

---

## Sending

```bash
# Send everything in queue
nmail send

# Send specific draft
nmail send ~/Mail/drafts/meeting.md

# Send with retries
nmail send --retry 3

# Preview what would be sent (dry-run)
nmail send --dry-run | bat --language=email

# Send only pending (not failed)
nmail send        # (only drains queue/new/)

# Retry failed sends
nmail send --all  # (includes queue/cur/ failures)
```

---

## Searching

```bash
# Full-text search for invoice
nmail search invoice

# Search with notmuch tags
nmail search tag:unread from:alice

# Interactive search → open
nmail search --interactive tag:unread

# Search → archive all results (read from stdin)
nmail search --format ids tag:todo \
  | nmail archive -

# Search → tag all results
nmail search --format ids from:bob \
  | nmail tag +bob -

# Search → forward each result to someone
nmail search --format paths subject:report \
  | while read msg; do nmail forward "$msg" --to manager@example.com; done
```

---

## Tagging

```bash
# Tag all from Bob
nmail search --format ids from:bob | nmail tag +bob -

# Remove unread tag (mark as read)
nmail tag -unread 182 193 204

# Tag chain: find → tag → archive
nmail search --format ids subject:newsletter \
  | nmail tag +newsletter - \
  && nmail search --format ids tag:newsletter \
  | nmail archive -
```

---

## Archiving and Trashing

```bash
# Archive by age (flat mode)
find ~/Mail/incoming/cur -mtime +30 | xargs nmail archive

# Archive by age (profile-aware)
find ~/Mail/personal/incoming/cur -mtime +30 | xargs nmail archive
find ~/Mail/work/incoming/cur -mtime +30 | xargs nmail archive

# Trash old sent mail
find ~/Mail/sent/cur -mtime +365 | xargs nmail trash
find ~/Mail/personal/sent/cur -mtime +365 | xargs nmail trash

# Empty trash older than 30 days
nmail trash --age 30 --force

# Archive all from mailing list
nmail search --format ids from:lists.example.com | nmail archive -
```

---

## Contacts

```bash
# Find Alice's email
nmail contacts alice

# Interactive contact picker → compose
nmail contacts \
  | fzf --preview 'echo {}' \
  | cut -f2 \
  | xargs -I{} nmail compose --to {}

# Rebuild contact database
nmail contacts --update

# Export contacts
nmail contacts --format json | jq '.[] | select(.count > 10)'
```

---

## Status and Monitoring

```bash
# Check status
nmail status

# Watch status (refresh every 10s)
watch -n 10 nmail status

# JSON status for scripting
nmail status --json | jq '.queue | "pending: \(.pending), failed: \(.failed)"'

# Count messages per tag
for tag in inbox unread todo archive; do
  printf "%-10s %s\n" "$tag:" "$(notmuch count tag:$tag)"
done
```

---

## Templates

```bash
# List templates
nmail template list

# Create template from existing draft
cp ~/Mail/drafts/good-draft.md ~/Mail/templates/project-update.md
nmail template edit project-update

# Compose from template with fzf picker
nmail template list | fzf | xargs nmail compose
```

---

## Logs

```bash
# Follow live log
nmail log --follow

# Errors in last hour
nmail log --since 1h --level 3

# All send events today
nmail log --since 2026-07-13 --event send

# Count sync events
nmail log --event sync --json | jq -s 'length'

# Recent new mail notifications
nmail log --event new --json | jq -r '"\(.ts) — \(.count) new"'
```

---

## Attachments

```bash
# List attachments from message 182
nmail attach list 182

# Save first attachment
nmail attach save 182 ./file.pdf

# Extract all PDFs from unread mail
nmail search --format paths tag:unread \
  | while read msg; do
      nmail attach save "$msg" "./attachments/"
    done
```

---

## Advanced Pipelines

```bash
# Find all GitHub notification emails → tag → archive
nmail search --format ids from:notifications@github.com \
  | nmail tag +github - \
  && sleep 1 \
  && nmail search --format ids tag:github \
  | nmail archive -

# Daily digest: count by sender
nmail search --format paths --limit 0 \
  | xargs grep -h '^From:' \
  | sort | uniq -c | sort -rn | head -20

# Reply to all unread with template
nmail search --format paths tag:unread \
  | while read msg; do
      nmail reply "$msg" --template quick-reply
    done

# Find messages with attachments
nmail search --format paths "" \
  | xargs grep -l 'Content-Disposition: attachment' \
  | while read msg; do nmail tag +has-attachment "$msg"; done

# Pipe rendered email to spellcheck
nmail render ~/Mail/queue/new/abc123 | aspell list

# Generate report: messages per day this week
nmail search --format paths --sort oldest-first --limit 0 \
  | xargs stat -c '%y' \
  | cut -d' ' -f1 \
  | sort | uniq -c

# Batch reply: same template to multiple threads
for id in 182 193 204; do
  cat template.md | nmail reply "$id" --stdin
done

# Sync → index → notify pipeline
nmail sync && notmuch new && nmail status --json \
  | jq -r '"New: \(.incoming.new), Total: \(.incoming.total)"' \
  | xargs notify-send "Mail"
```

---

## fzf Integration Patterns

```bash
# fzf-based mail browser
function nmail-fzf() {
  nmail search --format paths "$@" \
    | while read f; do
        subj=$(grep -m1 '^Subject:' "$f" | sed 's/^Subject: //')
        from=$(grep -m1 '^From:' "$f" | sed 's/^From: //')
        date=$(grep -m1 '^Date:' "$f" | sed 's/^Date: //')
        printf '%s\t%s\t%s\t%s\n' "$date" "$from" "$subj" "$f"
      done \
    | fzf --delimiter='\t' \
          --with-nth=2,3 \
          --preview='bat --language=email --color=always {4}' \
          --preview-window=right:60% \
    | cut -f4 \
    | xargs -r nmail open
}

# Usage: nmail-fzf tag:unread
# Usage: nmail-fzf from:alice
```

## rg Fallback (no notmuch)

```bash
# Search all mail with ripgrep
function nmail-grep() {
  # Single profile
  rg -l "$1" ~/Mail/incoming/ ~/Mail/archive/ ~/Mail/sent/
  # Multi-profile: add ~/Mail/personal/ ~/Mail/work/
  rg -l "$1" ~/Mail/*/incoming/ ~/Mail/*/archive/ ~/Mail/*/sent/
}

# fzf with rg
function nmail-fzf-grep() {
  rg -l "$1" ~/Mail/*/incoming/ ~/Mail/*/archive/ ~/Mail/*/sent/ \
    | while read f; do
        subj=$(grep -m1 '^Subject:' "$f" | sed 's/^Subject: //')
        printf '%s\t%s\n' "$subj" "$f"
      done \
    | fzf --delimiter='\t' \
          --with-nth=1 \
          --preview='bat --language=email {2}' \
    | cut -f2 \
    | xargs -r nmail open
}
```
