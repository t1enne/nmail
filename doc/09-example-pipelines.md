# Example Shell Pipelines

> All examples assume `~/Mail/` exists and commands are in `PATH`.

---

## 1. Quick Status Check

```bash
$ mail-status
Incoming:  3 new, 147 total
Archive:   1204 total
Sent:      89 total
Drafts:    2 pending
Queue:     1 pending, 0 failed
Trash:     23 total
Last sync: 2026-07-13 14:30:00
```

---

## 2. Search and Open

```bash
# Find all unread from Alice, pick with fzf preview, open
$ mail-search --format paths tag:unread from:alice \
  | while read f; do
      subj=$(grep -m1 '^Subject:' "$f" | sed 's/^Subject: //')
      date=$(grep -m1 '^Date:' "$f" | sed 's/^Date: //')
      printf '%s  %s\t%s\n' "$date" "$subj" "$f"
    done \
  | fzf --with-nth=1.. --preview='bat --language=email {2}' \
  | awk '{print $NF}' \
  | xargs mail-open
```

---

## 3. Compose → Queue → Send

```bash
# Compose a new message
$ mail-compose --to alice@example.com --subject "Meeting tomorrow"

# nvim opens, user writes:
#   Hello Alice,
#   Let's meet at 2pm.
#   Thanks,
#   John
# User saves and exits (:wq)

# mail-compose validates and moves to queue/new/

$ mail-status
Queue: 1 pending

# Send (via cron, systemd timer, or manual)
$ mail-send

$ mail-status
Queue: 0 pending

$ mail-log --since 1m
[2026-07-13T14:32:00Z] mail:sent abc123
```

---

## 4. Reply Pipeline

```bash
# See new mail from Bob
$ mail-search tag:unread from:bob --format summary
2026-07-13 14:00  Bob Smith   Re: Project update    [id:204]

# Reply
$ mail-reply 204

# nvim opens with:
#   To: Bob Smith <bob@example.com>
#   Subject: Re: Project update
#   ...
#   On ..., Bob Smith wrote:
#   > original text quoted

# Write reply, save, exit. Draft queued.

# Send later
$ mail-send
```

---

## 5. Batch Tagging and Archiving

```bash
# Tag all newsletters
$ mail-search --format ids from:newsletter@example.com | mail-tag +newsletter -

# Tag all from work domain
$ mail-search --format ids from:@company.com | mail-tag +work -

# Archive all read newsletters older than 30 days
$ mail-search --format paths tag:newsletter \
  | xargs ls -t \
  | tail -n +30 \
  | mail-archive -
```

---

## 6. Contacts Workflow

```bash
# Find Alice's addresses
$ mail-contacts alice
Alice Smith    alice@example.com      47
Alice Wong     alice.w@company.com    12

# Interactive picker → compose
$ mail-contacts \
  | fzf --header='Pick recipient' \
  | awk '{print $2}' \
  | xargs -I{} mail-compose --to {}

# Rebuild cache (run in cron weekly)
$ mail-contacts --update
```

---

## 7. Log Monitoring

```bash
# Follow log in real-time
$ mail-log --follow
{"ts":"2026-07-13T14:30:00Z","event":"mail:sync-end","count":3}
{"ts":"2026-07-13T14:30:01Z","event":"mail:new","count":3}
{"ts":"2026-07-13T14:32:00Z","event":"mail:sent","id":"abc123"}
...

# Check for errors today
$ mail-log --since 24h --level 3
{"ts":"2026-07-13T10:15:00Z","event":"mail:error","id":"def456","error":"SMTP timeout"}

# Count events by type
$ mail-log --json --since 7d \
  | jq -r '.event' \
  | sort | uniq -c | sort -rn
34 mail:sync-end
15 mail:new
 8 mail:sent
 2 mail:error
```

---

## 8. Queue Management

```bash
# See what's in queue
$ ls ~/Mail/queue/new/ | wc -l
3

# Preview first queued message
$ mail-render ~/Mail/queue/new/$(ls ~/Mail/queue/new/ | head -1) \
  | bat --language=email

# Send all
$ mail-send
Sent 3 messages. 0 failed.

# Check for failures
$ ls ~/Mail/queue/cur/ | wc -l
0

# Retry failed sends
$ mail-send --all
```

---

## 9. Attachment Extraction

```bash
# Find messages with attachments
$ mail-search --format paths "" | xargs grep -l 'Content-Disposition: attachment'

# Save attachment from message 182
$ mail-attach save 182 ./report.pdf

# Save all PDFs from unread
$ mail-search --format paths tag:unread \
  | while read msg; do
      id=$(basename "$msg" | cut -d: -f1)
      mail-attach save "$id" ~/Downloads/
    done
```

---

## 10. Coworker Onboarding (nmail setup)

```bash
# 1. Install
$ git clone https://github.com/user/nmail ~/dev/nmail
$ cd ~/dev/nmail && ./install.sh

# 2. Configure msmtp and mbsync (one-time)
$ $EDITOR ~/.msmtprc
$ $EDITOR ~/.mbsyncrc

# 3. Edit nmail config
$ $EDITOR ~/.config/nmail/config.toml

# 4. Initial sync
$ mail-sync

# 5. Launch workspace
$ mail-session

# tmux session opens:
# ┌──────────┬──────────┐
# │ compose  │ inbox    │
# ├──────────┼──────────┤
# │ shell    │ search   │
# └──────────┴──────────┘
```

---

## 11. Daily Workflow

```bash
# Morning: check new mail
$ mail-sync

# or just launch session (syncs on start)
$ mail-session

# In tmux:
#   Top-left pane (nvim): compose replies
#   Top-right pane (lf): browse inbox
#   Bottom-left: tail -f logs
#   Bottom-right: mail-search --interactive tag:unread

# Read important mail
# In search pane: mail-search tag:unread --interactive
# fzf picker → Enter to open → read → :q
# Back in search pane: mail-reply <id> (composes in top-left pane)

# Archive after reading
# In inbox pane (lf): select message → press 'a' (maps to mail-archive)

# Compose new
# In top-left pane: :e new-draft.md
# Write, save: :wq
# Auto-queued. Sent by background process.

# End of day: check queue
$ mail-status
$ mail-send   # flush anything remaining
```

---

## 12. Power User: Full Scripting

```bash
#!/bin/bash
# daily-digest.sh — send a daily summary to yourself

DIGEST=$(mktemp)

echo "Daily Mail Digest — $(date +%Y-%m-%d)" > "$DIGEST"
echo >> "$DIGEST"

echo "## Unread" >> "$DIGEST"
mail-search --format summary tag:unread --limit 20 >> "$DIGEST"

echo >> "$DIGEST"
echo "## Sent Today" >> "$DIGEST"
mail-status --json | jq -r '.sent' >> "$DIGEST"

echo >> "$DIGEST"
echo "## Errors" >> "$DIGEST"
mail-log --since 24h --level 3 --json \
  | jq -r '"  - \(.error)"' >> "$DIGEST"

mail-compose --to me@example.com --subject "Daily Digest" --stdin < "$DIGEST"
mail-send

rm "$DIGEST"
```

```bash
#!/bin/bash
# auto-tag.sh — auto-tag messages based on rules

while IFS='|' read -r pattern tag; do
    mail-search --format ids "from:$pattern AND NOT tag:$tag" \
        | mail-tag "+$tag" -
done < ~/.config/nmail/auto-tags.tsv
```

`auto-tags.tsv`:
```
notifications@github.com|github
newsletter@example.com|newsletter
@company.com|work
```

---

## 13. Integration with External Tools

```bash
# Use mu instead of notmuch for search
$ alias mail-search='mu find --format=plain'

# Use yazi instead of lf in mail-session
$ NM_FILE_BROWSER=yazi mail-session

# Use glow to render markdown emails
$ mail-open 182 | glow -

# Use delta for diffing draft revisions
$ diff <(mail-render draft-v1.md) <(mail-render draft-v2.md) | delta

# Export to MBOX
$ find ~/Mail/archive/cur -type f | xargs cat > archive.mbox
```

---

## 14. Systemd Integration

```ini
# ~/.config/systemd/user/nmail-sync.timer
[Unit]
Description=Mail sync timer

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# ~/.config/systemd/user/nmail-sync.service
[Unit]
Description=Mail sync

[Service]
Type=oneshot
ExecStart=%h/.local/bin/mail-sync
```

```ini
# ~/.config/systemd/user/nmail-send.timer
[Unit]
Description=Queue drain timer

[Timer]
OnCalendar=*:0/2
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# ~/.config/systemd/user/nmail-send.service
[Unit]
Description=Drain mail queue

[Service]
Type=oneshot
ExecStart=%h/.local/bin/mail-send
```

```bash
# Enable timers
$ systemctl --user enable --now nmail-sync.timer
$ systemctl --user enable --now nmail-send.timer

# Check status
$ systemctl --user status nmail-sync.timer
$ systemctl --user status nmail-send.timer
```
