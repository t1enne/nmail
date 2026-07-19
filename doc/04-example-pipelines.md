# Example Shell Pipelines

> All examples assume `~/Mail/` exists and `nmail` is in `PATH`.
>
> For multi-profile setups (`~/Mail/personal/`, `~/Mail/work/`), replace flat paths like
> `~/Mail/incoming/` with `~/Mail/<profile>/incoming/` or use globs like `~/Mail/*/incoming/`.

---

## 1. Quick Status Check

```bash
$ nmail status
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
$ nmail search --format paths tag:unread from:alice \
  | while read f; do
      subj=$(grep -m1 '^Subject:' "$f" | sed 's/^Subject: //')
      date=$(grep -m1 '^Date:' "$f" | sed 's/^Date: //')
      printf '%s  %s\t%s\n' "$date" "$subj" "$f"
    done \
  | fzf --with-nth=1.. --preview='bat --language=email {2}' \
  | awk '{print $NF}' \
  | xargs nmail open
```

---

## 3. Compose → Queue → Send

```bash
# Compose a new message
$ nmail compose --to alice@example.com --subject "Meeting tomorrow"

# nvim opens, user writes draft, saves and exits (:wq)
# nmail compose validates and moves to queue/new/

$ nmail status
Queue: 1 pending

# Send
$ nmail send

$ nmail status
Queue: 0 pending

$ nmail log --since 1m
[2026-07-13T14:32:00Z] mail:sent abc123
```

---

## 4. Reply Pipeline

```bash
# See new mail from Bob
$ nmail search tag:unread from:bob --format summary
2026-07-13 14:00  Bob Smith   Re: Project update    [id:204]

# Reply
$ nmail reply 204

# nvim opens with:
#   To: Bob Smith <bob@example.com>
#   Subject: Re: Project update
#   In-Reply-To: <original-message-id>
#   References: <accumulated>
#   ---
#   On ..., Bob Smith wrote:
#   > original text quoted

# Write reply, save, exit. Draft queued.
# Send later
$ nmail send
```

---

## 5. Batch Tagging and Archiving

```bash
# Tag all newsletters
$ nmail search --format ids from:newsletter@example.com | nmail tag +newsletter -

# Tag all from work domain
$ nmail search --format ids from:@company.com | nmail tag +work -

# Archive all read newsletters older than 30 days
$ nmail search --format paths tag:newsletter \
  | xargs ls -t \
  | tail -n +30 \
  | nmail archive -
```

---

## 6. Contacts Workflow

```bash
# Find Alice's addresses
$ nmail contacts alice
Alice Smith    alice@example.com      47
Alice Wong     alice.w@company.com    12

# Interactive picker → compose
$ nmail contacts \
  | fzf --header='Pick recipient' \
  | awk '{print $2}' \
  | xargs -I{} nmail compose --to {}

# Rebuild cache (run in cron weekly)
$ nmail contacts --update
```

---

## 7. Log Monitoring

```bash
# Follow log in real-time
$ nmail log --follow
{"ts":"2026-07-13T14:30:00Z","event":"mail:sync-end","count":3}
{"ts":"2026-07-13T14:30:01Z","event":"mail:new","count":3}
{"ts":"2026-07-13T14:32:00Z","event":"mail:sent","id":"abc123"}
...

# Check for errors today
$ nmail log --since 24h --level 3
{"ts":"2026-07-13T10:15:00Z","event":"mail:error","id":"def456","error":"SMTP timeout"}

# Count events by type
$ nmail log --json --since 7d \
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
$ nmail render ~/Mail/queue/new/$(ls ~/Mail/queue/new/ | head -1) \
  | bat --language=email

# Send all
$ nmail send
Sent 3 messages. 0 failed.

# Check for failures
$ ls ~/Mail/queue/cur/ | wc -l
0

# Retry failed sends
$ nmail send --all
```

---

## 9. Attachment Extraction

```bash
# Find messages with attachments
$ nmail search --format paths "" | xargs grep -l 'Content-Disposition: attachment'

# Save attachment from message 182
$ nmail attach save 182 ./report.pdf

# Save all PDFs from unread
$ nmail search --format paths tag:unread \
  | while read msg; do
      id=$(basename "$msg" | cut -d: -f1)
      nmail attach save "$id" ~/Downloads/
    done
```

---

## 10. Coworker Onboarding (nmail setup)

```bash
# 1. Install
$ git clone https://github.com/user/nmail ~/dev/nmail
$ cd ~/dev/nmail && uv sync

# 2. Configure msmtp and mbsync (one-time)
$ $EDITOR ~/.msmtprc
$ $EDITOR ~/.mbsyncrc

# 3. Edit nmail config
$ $EDITOR ~/.config/nmail/config.toml

# 4. Initial sync
$ nmail sync
```

---

## 11. Daily Workflow

```bash
# Morning: check new mail
$ nmail sync

# Read new mail
$ nmail search --interactive tag:unread

# Compose new
$ nmail compose --to "team@example.com" --subject "Daily standup notes"

# End of day: check queue
$ nmail status
$ nmail send   # flush anything remaining
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
nmail search --format summary tag:unread --limit 20 >> "$DIGEST"

echo >> "$DIGEST"
echo "## Sent Today" >> "$DIGEST"
nmail status --json | jq -r '.sent' >> "$DIGEST"

echo >> "$DIGEST"
echo "## Errors" >> "$DIGEST"
nmail log --since 24h --level 3 --json \
  | jq -r '"  - \(.error)"' >> "$DIGEST"

nmail compose --to me@example.com --subject "Daily Digest" --stdin < "$DIGEST"
nmail send

rm "$DIGEST"
```

```bash
#!/bin/bash
# auto-tag.sh — auto-tag messages based on rules

while IFS='|' read -r pattern tag; do
    nmail search --format ids "from:$pattern AND NOT tag:$tag" \
        | nmail tag "+$tag" -
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
$ alias nmail search='mu find --format=plain'

# Use glow to render markdown emails
$ nmail open 182 | glow -

# Use delta for diffing draft revisions
$ diff <(nmail render draft-v1.md) <(nmail render draft-v2.md) | delta

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
ExecStart=%h/.local/bin/nmail sync

[Install]
WantedBy=timers.target
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
ExecStart=%h/.local/bin/nmail send

[Install]
WantedBy=timers.target
```

```bash
# Enable timers
$ systemctl --user enable --now nmail-sync.timer
$ systemctl --user enable --now nmail-send.timer

# Check status
$ systemctl --user status nmail-sync.timer
$ systemctl --user status nmail-send.timer
```
