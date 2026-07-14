#!/usr/bin/env bash
# common.sh — shared utilities for all nmail commands
#
# Source this in every mail-* script:
#   source "${NM_LIBDIR:-$HOME/.local/lib/nmail}/common.sh"

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

NM_CONFIG="${NM_CONFIG:-$HOME/.config/nmail/config.toml}"
NM_MAILDIR="${NM_MAILDIR:-$HOME/Mail}"
NM_STATEDIR="${NM_STATEDIR:-$HOME/.local/state/nmail}"
NM_LOGDIR="${NM_LOGDIR:-$NM_MAILDIR/logs}"
NM_LOG="${NM_LOG:-$NM_LOGDIR/mail.log}"
NM_HOOKSDIR="${NM_HOOKSDIR:-$HOME/.config/nmail/hooks.d}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# log_event <event> [args...]
# Writes structured JSON log line and optionally fires hooks.
log_event() {
    local event="$1"; shift
    local ts
    ts=$(date -Iseconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")

    mkdir -p "$(dirname "$NM_LOG")"

    # Build JSON line
    local json
    json=$(jq -nc \
        --arg ts "$ts" \
        --arg event "$event" \
        --argjson args "$(printf '%s\n' "$@" | jq -R . | jq -s .)" \
        '{ts: $ts, event: $event, args: $args}')

    echo "$json" >> "$NM_LOG"

    # Fire hooks if hooks directory exists
    if [[ -d "$NM_HOOKSDIR" ]]; then
        local hook_name="${event#mail:}"  # "mail:new" → "new"
        for hook in "$NM_HOOKSDIR"/on-"$hook_name"*; do
            if [[ -x "$hook" ]]; then
                "$hook" "$event" "$@" || true  # never fail on hook errors
            fi
        done
    fi
}

# log_info <message>
log_info() {
    log_event "info" "$@"
}

# log_warn <message>
log_warn() {
    log_event "warn" "$@"
}

# log_error <message>
log_error() {
    log_event "error" "$@"
}

# ---------------------------------------------------------------------------
# Configuration (simple TOML reader)
# ---------------------------------------------------------------------------

# config_get <key.path> — reads value from config.toml
# Uses basic grep+sed. For complex TOML, use yq or tomlq.
config_get() {
    local key="$1"
    local file="${NM_CONFIG}"

    if [[ ! -f "$file" ]]; then
        echo ""
        return 1
    fi

    # Very basic TOML: section.key → grep section, then grep key
    local section keyname
    section=$(echo "$key" | cut -d. -f1)
    keyname=$(echo "$key" | cut -d. -f2-)

    # Extract value after '=' in the right section
    awk -v section="$section" -v key="$keyname" '
        /^\[/ { in_section = ($0 ~ "\\[" section "\\]") }
        in_section && $0 ~ "^" key " *= *" {
            sub("^[^=]*= *", "")
            sub(" *#.*$", "")
            gsub("^\"|\"$", "")
            print
            exit
        }
    ' "$file"
}

# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------

# open_editor <file>
open_editor() {
    local file="$1"
    local editor="${EDITOR:-nvim}"

    if [[ -n "${NM_DRY_RUN:-}" ]]; then
        echo "[DRY-RUN] Would open: $editor $file"
        return 0
    fi

    $editor "$file"
}

# ---------------------------------------------------------------------------
# Maildir operations
# ---------------------------------------------------------------------------

# maildir_move <src> <dst-dir>
# Moves a file between Maildir directories atomically.
maildir_move() {
    local src="$1"
    local dstdir="$2"

    if [[ ! -f "$src" ]]; then
        echo "maildir_move: source not found: $src" >&2
        return 1
    fi

    local dst="$dstdir/$(basename "$src")"

    if [[ -n "${NM_DRY_RUN:-}" ]]; then
        echo "[DRY-RUN] Would move: $src → $dst"
        return 0
    fi

    mkdir -p "$(dirname "$dst")"
    mv "$src" "$dst"
}

# maildir_new_id — generate a unique Maildir filename
maildir_new_id() {
    local host
    host=$(hostname 2>/dev/null || echo "localhost")
    printf "%s.%s.%s" \
        "$(date +%s)" \
        "$$" \
        "$host"
}

# maildir_count <directory>
maildir_count() {
    local dir="$1"
    find "$dir" -type f 2>/dev/null | wc -l
}

# ---------------------------------------------------------------------------
# Headers extraction
# ---------------------------------------------------------------------------

# extract_header <file> <header-name>
extract_header() {
    local file="$1"
    local header="$2"
    grep -m1 "^${header}:" "$file" 2>/dev/null | sed "s/^${header}: *//" || echo ""
}

# extract_body <file>
# Gets everything after the first blank line (or after "---" separator).
extract_body() {
    local file="$1"
    local sep="---"

    if grep -q "^$sep$" "$file"; then
        sed -n "/^$sep$/,\$p" "$file" | tail -n +2
    else
        # Fallback: first blank line
        awk 'found { print; next } /^$/ { found=1 }' "$file"
    fi
}

# ---------------------------------------------------------------------------
# Message ID resolution
# ---------------------------------------------------------------------------

# resolve_id <id> — resolve a message ID to a file path
# Tries: notmuch, then glob over Maildir
resolve_id() {
    local id="$1"

    # Try notmuch first
    if command -v notmuch &>/dev/null; then
        local result
        result=$(notmuch search --output=files "id:$id" 2>/dev/null || true)
        if [[ -n "$result" ]]; then
            echo "$result" | head -1
            return 0
        fi
    fi

    # Fallback: glob for files containing the ID
    local found
    found=$(find "$NM_MAILDIR" -name "*${id}*" -type f 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi

    return 1
}

# ---------------------------------------------------------------------------
# Mark read
# ---------------------------------------------------------------------------

# mark_read <file>
# Moves message from new/ to cur/ if it's in a Maildir new/ directory.
mark_read() {
    local file="$1"
    local dir
    dir=$(dirname "$file")

    if [[ "$dir" == */new ]]; then
        local curdir="${dir%/new}/cur"
        maildir_move "$file" "$curdir"
    fi
}

# ---------------------------------------------------------------------------
# Draft validation
# ---------------------------------------------------------------------------

# validate_draft <file>
# Returns 0 if draft has required headers (To:, Subject:).
validate_draft() {
    local file="$1"

    if [[ ! -s "$file" ]]; then
        echo "Draft is empty" >&2
        return 1
    fi

    local to subject
    to=$(extract_header "$file" "To")
    subject=$(extract_header "$file" "Subject")

    if [[ -z "$to" ]]; then
        echo "Missing To: header" >&2
        return 1
    fi

    if [[ -z "$subject" ]]; then
        echo "Missing Subject: header" >&2
        return 1
    fi

    return 0
}

# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

# queue_draft <draft-file>
# Moves draft to queue/new/.
queue_draft() {
    local draft="$1"
    local id
    id=$(maildir_new_id)

    local dest="$NM_MAILDIR/queue/new/$id"

    if [[ -n "${NM_DRY_RUN:-}" ]]; then
        echo "[DRY-RUN] Would queue: $draft → $dest"
        return 0
    fi

    mkdir -p "$(dirname "$dest")"
    cp "$draft" "$dest"
    log_event "mail:draft" "$dest"
    echo "$dest"
}

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

# ensure_maildir — create all Maildir directories
ensure_maildir() {
    local dirs=(
        incoming/cur incoming/new incoming/tmp
        archive/cur
        drafts
        sent/cur sent/new sent/tmp
        trash/cur trash/new trash/tmp
        attachments
        queue/cur queue/new queue/tmp
        templates
        logs
    )

    for d in "${dirs[@]}"; do
        mkdir -p "$NM_MAILDIR/$d"
    done

    mkdir -p "$NM_STATEDIR"
}
