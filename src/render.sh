#!/usr/bin/env bash
# render.sh — Markdown draft → RFC5322 MIME message
#
# Usage: source this file, then call render_message <draft-file>
# Or:   mail-render <draft-file>  (when symlinked as mail-render)

set -euo pipefail

# Source common if not already loaded
if ! declare -f log_event &>/dev/null; then
    NM_LIBDIR="${NM_LIBDIR:-$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")}"
    source "${NM_LIBDIR}/common.sh"
fi

# ---------------------------------------------------------------------------
# Parse draft into parts
# ---------------------------------------------------------------------------

# parse_draft <file>
# Sets global variables: HEADERS, BODY (markdown), ATTACHMENTS
parse_draft() {
    local file="$1"

    HEADERS=$(sed '/^---$/q' "$file" | head -n -1)  # everything before first ---
    BODY=$(sed -n '/^---$/,$p' "$file" | tail -n +2)  # everything after first ---

    # Check for second --- separator (attachment list)
    if echo "$BODY" | grep -q '^---$'; then
        ATTACHMENTS=$(echo "$BODY" | sed -n '/^---$/,$p' | tail -n +2)
        BODY=$(echo "$BODY" | sed '/^---$/q')
    else
        ATTACHMENTS=""
    fi
}

# ---------------------------------------------------------------------------
# Generate MIME boundary
# ---------------------------------------------------------------------------

mime_boundary() {
    echo "========nm=$(date +%s)==$(od -A n -t x4 -N 8 /dev/urandom | tr -d ' ')=="
}

# ---------------------------------------------------------------------------
# Build full MIME message
# ---------------------------------------------------------------------------

# render_message <draft-file> [--format plain|mime|html]
# Outputs RFC5322 to stdout.
render_message() {
    local file="$1"
    local format="${2:-mime}"

    if [[ ! -f "$file" ]]; then
        echo "render_message: file not found: $file" >&2
        return 1
    fi

    parse_draft "$file"

    # Extract key headers (|| true for optional ones)
    local to cc bcc subject from date msgid
    to=$(echo "$HEADERS" | grep -i '^To:' | sed 's/^[^:]*: *//' || true)
    cc=$(echo "$HEADERS" | grep -i '^Cc:' | sed 's/^[^:]*: *//' || true)
    bcc=$(echo "$HEADERS" | grep -i '^Bcc:' | sed 's/^[^:]*: *//' || true)
    subject=$(echo "$HEADERS" | grep -i '^Subject:' | sed 's/^[^:]*: *//' || true)
    from=$(echo "$HEADERS" | grep -i '^From:' | sed 's/^[^:]*: *//' || true)

    # Defaults
    if [[ -z "$from" ]]; then
        from="${MAIL_FROM:-$(config_get general.from_address)}"
        [[ -z "$from" ]] && from="${USER}@$(hostname -f 2>/dev/null || hostname)"
    fi

    date=$(date -R 2>/dev/null || date)
    msgid="<$(date +%s).$$@$(hostname -f 2>/dev/null || hostname)>"

    # Plain text only
    if [[ "$format" == "plain" ]]; then
        echo "From: $from"
        [[ -n "$to" ]] && echo "To: $to"
        [[ -n "$cc" ]] && echo "Cc: $cc"
        [[ -n "$bcc" ]] && echo "Bcc: $bcc"
        echo "Subject: $subject"
        echo "Date: $date"
        echo "Message-ID: $msgid"
        echo "MIME-Version: 1.0"
        echo "Content-Type: text/plain; charset=utf-8"
        echo "Content-Transfer-Encoding: 8bit"
        echo
        echo "$BODY"
        return 0
    fi

    # HTML only (for preview)
    if [[ "$format" == "html" ]]; then
        if command -v pandoc &>/dev/null; then
            echo "$BODY" | pandoc -f markdown -t html --standalone
        else
            echo "<pre>"
            echo "$BODY" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
            echo "</pre>"
        fi
        return 0
    fi

    # Full MIME
    local boundary
    boundary=$(mime_boundary)

    # Build message headers
    echo "From: $from"
    [[ -n "$to" ]] && echo "To: $to"
    [[ -n "$cc" ]] && echo "Cc: $cc"
    [[ -n "$bcc" ]] && echo "Bcc: $bcc"
    echo "Subject: $subject"
    echo "Date: $date"
    echo "Message-ID: $msgid"
    echo "MIME-Version: 1.0"
    echo "Content-Type: multipart/alternative; boundary=\"$boundary\""
    echo

    # Part 1: text/plain (markdown as-is)
    echo "--$boundary"
    echo "Content-Type: text/plain; charset=utf-8"
    echo "Content-Transfer-Encoding: 8bit"
    echo
    echo "$BODY"
    echo

    # Part 2: text/html (pandoc conversion)
    echo "--$boundary"
    echo "Content-Type: text/html; charset=utf-8"
    echo "Content-Transfer-Encoding: 8bit"
    echo
    if command -v pandoc &>/dev/null; then
        echo "$BODY" | pandoc -f markdown -t html
    else
        echo "<html><body><pre>"
        echo "$BODY" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
        echo "</pre></body></html>"
    fi
    echo

    # Part 3+: Attachments
    if [[ -n "$ATTACHMENTS" ]]; then
        local attach_boundary
        attach_boundary=$(mime_boundary)

        # We need to wrap in a multipart/mixed
        # This is simplified — for proper nested MIME, attachments are added
        # as subsequent parts. For now: list them but don't encode.
        #
        # Full implementation would:
        # 1. Rewrite headers as multipart/mixed with new boundary
        # 2. Include multipart/alternative as first sub-part
        # 3. Add each attachment as base64-encoded part
        echo "--- Attachments (not encoded in MIME): ---"
        echo "$ATTACHMENTS"
        echo "---"
    fi

    echo "--$boundary--"
}

# render.sh is a library — use bin/mail-render for CLI
