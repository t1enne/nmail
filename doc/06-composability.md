# Composability: Example Shell Pipelines

## Philosophy

Every `mail-*` command is a Unix filter. Input from stdin/files, output to stdout/files.
Compose with pipes, xargs, fzf, jq, etc. No monolithic client needed.

---

## Reading Mail

```bash
# Open most recent 10 messages, pick one with fzf
mail-search --format paths tag:unread --limit 50 \
  | while read f; do echo "$(head -50 "$f" | grep '^Subject:' | head -1)  $f"; done \
  | fzf --preview 'bat --language=email {2}' \
  | awk '{print $NF}' \
  | xargs mail-open

# Open oldest unread
mail-search --format paths --sort oldest-first tag:unread --limit 1 \
  | xargs mail-open

# Count unread
mail-search tag:unread --limit 0 2>&1 | grep -oP 'Found \K\d+'
# Or: mail-status --json | jq '.incoming.new'
```

---

## Composing

```bash
# Compose new mail to Alice
mail-compose --to alice@example.com --subject "Meeting notes"

# Compose from template
mail-compose meeting --to team@example.com

# Compose and queue immediately (non-interactive)
echo -e "To: bob@example.com\nSubject: Test\n\n---\n\nHello." \
  | mail-compose --stdin

# Batch compose from file list
while read to subject; do
  mail-compose --to "$to" --subject "$subject"
done < recipients.txt
```

---

## Sending

```bash
# Send everything in queue
mail-send

# Send specific draft
mail-send ~/Mail/drafts/meeting.md

# Send with retries
mail-send --retry 3

# Preview what would be sent (dry-run)
mail-send --dry-run | bat --language=email

# Send only pending (not failed)
mail-send        # (only drains queue/new/)

# Retry failed sends
mail-send --all  # (includes queue/cur/ failures)
```

---

## Searching

```bash
# Full-text search for invoice
mail-search invoice

# Search with notmuch tags
mail-search tag:unread from:alice

# Interactive search → open
mail-search --interactive tag:unread

# Search → archive all results (read from stdin)
mail-search --format ids tag:todo \
  | mail-archive -

# Search → tag all results
mail-search --format ids from:bob \
  | mail-tag +bob -

# Search → forward each result to someone
mail-search --format paths subject:report \
  | while read msg; do mail-forward "$msg" --to manager@example.com; done
```

---

## Tagging

```bash
# Tag all from Bob
mail-search --format ids from:bob | mail-tag +bob -

# Remove unread tag (mark as read)
mail-tag -unread 182 193 204

# Tag chain: find → tag → archive
mail-search --format ids subject:newsletter \
  | mail-tag +newsletter - \
  && mail-search --format ids tag:newsletter \
  | mail-archive -
```

---

## Archiving and Trashing

```bash
# Archive all read messages
mail-search --format paths tag:unread --limit 0 >/dev/null  # not much
# Better: archive by age
find ~/Mail/incoming/cur -mtime +30 | xargs mail-archive

# Trash old sent mail
find ~/Mail/sent/cur -mtime +365 | xargs mail-trash

# Empty trash older than 30 days
mail-trash --age 30 --force

# Archive all from mailing list
mail-search --format ids from:lists.example.com | mail-archive -
```

---

## Contacts

```bash
# Find Alice's email
mail-contacts alice

# Interactive contact picker → compose
mail-contacts \
  | fzf --preview 'echo {}' \
  | cut -f2 \
  | xargs -I{} mail-compose --to {}

# Rebuild contact database
mail-contacts --update

# Export contacts
mail-contacts --format json | jq '.[] | select(.count > 10)'
```

---

## Status and Monitoring

```bash
# Check status
mail-status

# Watch status (refresh every 10s)
watch -n 10 mail-status

# JSON status for scripting
mail-status --json | jq '.queue | "pending: \(.pending), failed: \(.failed)"'

# Count messages per tag
for tag in inbox unread todo archive; do
  printf "%-10s %s\n" "$tag:" "$(notmuch count tag:$tag)"
done
```

---

## Templates

```bash
# List templates
mail-template list

# Create template from existing draft
cp ~/Mail/drafts/good-draft.md ~/Mail/templates/project-update.md
mail-template edit project-update

# Compose from template with fzf picker
mail-template list | fzf | xargs mail-compose
```

---

## Logs

```bash
# Follow live log
mail-log --follow

# Errors in last hour
mail-log --since 1h --level 3

# All send events today
mail-log --since 2026-07-13 --event send

# Count sync events
mail-log --event sync --json | jq -s 'length'

# Recent new mail notifications
mail-log --event new --json | jq -r '"\(.ts) — \(.count) new"'
```

---

## Attachments

```bash
# List attachments from message 182
mail-attach list 182

# Save first attachment
mail-attach save 182 ./file.pdf

# Extract all PDFs from unread mail
mail-search --format paths tag:unread \
  | while read msg; do
      mail-attach save "$msg" "./attachments/"
    done
```

---

## Advanced Pipelines

```bash
# Find all GitHub notification emails → tag → archive
mail-search --format ids from:notifications@github.com \
  | mail-tag +github - \
  && sleep 1 \
  && mail-search --format ids tag:github \
  | mail-archive -

# Daily digest: count by sender
mail-search --format paths --limit 0 \
  | xargs grep -h '^From:' \
  | sort | uniq -c | sort -rn | head -20

# Reply to all unread with template
mail-search --format paths tag:unread \
  | while read msg; do
      mail-reply "$msg" --template quick-reply
    done

# Find messages with attachments
mail-search --format paths "" \
  | xargs grep -l 'Content-Disposition: attachment' \
  | while read msg; do mail-tag +has-attachment "$msg"; done

# Pipe rendered email to a spellcheck
mail-render ~/Mail/queue/new/abc123 | aspell list

# Generate report: messages per day this week
mail-search --format paths --sort oldest-first --limit 0 \
  | xargs stat -c '%y' \
  | cut -d' ' -f1 \
  | sort | uniq -c

# Batch reply: same template to multiple threads
for id in 182 193 204; do
  cat template.md | mail-reply "$id" --stdin
done

# Sync → index → notify pipeline
mail-sync && notmuch new && mail-status --json \
  | jq -r '"New: \(.incoming.new), Total: \(.incoming.total)"' \
  | xargs notify-send "Mail"
```

---

## fzf Integration Patterns

```bash
# fzf-based mail browser
function mail-fzf() {
  mail-search --format paths "$@" \
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
    | xargs -r mail-open
}

# Usage: mail-fzf tag:unread
# Usage: mail-fzf from:alice
```

## rg Fallback (no notmuch)

```bash
# Search all mail with ripgrep
function mail-grep() {
  rg -l "$1" ~/Mail/incoming/ ~/Mail/archive/ ~/Mail/sent/
}

# fzf with rg
function mail-fzf-grep() {
  rg -l "$1" ~/Mail/incoming/ ~/Mail/archive/ ~/Mail/sent/ \
    | while read f; do
        subj=$(grep -m1 '^Subject:' "$f" | sed 's/^Subject: //')
        printf '%s\t%s\n' "$subj" "$f"
      done \
    | fzf --delimiter='\t' \
          --with-nth=1 \
          --preview='bat --language=email {2}' \
    | cut -f2 \
    | xargs -r mail-open
}
```
