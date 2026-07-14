#!/usr/bin/env bash
# notmuch.sh — notmuch integration with graceful fallback

if ! declare -f log_event &>/dev/null; then
    NM_LIBDIR="${NM_LIBDIR:-$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")}"
    source "${NM_LIBDIR}/common.sh"
fi

# ---------------------------------------------------------------------------
# Check if notmuch is available and configured
# ---------------------------------------------------------------------------

notmuch_available() {
    command -v notmuch &>/dev/null && \
    notmuch config get database.path &>/dev/null
}

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

# notmuch_search <query> [--output=files|messages|tags]
# Fallback: uses ripgrep over Maildir files.
notmuch_search() {
    local query=""
    local output="files"

    # Parse args
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output=*) output="${1#*=}"; shift ;;
            *) query="$1"; shift ;;
        esac
    done

    if notmuch_available; then
        notmuch search --output="$output" "$query" 2>/dev/null
    else
        # Fallback: ripgrep over Maildir
        if command -v rg &>/dev/null; then
            if [[ "$output" == "files" ]]; then
                rg -l --no-messages "$query" \
                    "$NM_MAILDIR/incoming/" \
                    "$NM_MAILDIR/archive/" \
                    "$NM_MAILDIR/sent/" 2>/dev/null || true
            else
                # Simplified: just output file paths regardless
                rg -l --no-messages "$query" \
                    "$NM_MAILDIR/incoming/" \
                    "$NM_MAILDIR/archive/" \
                    "$NM_MAILDIR/sent/" 2>/dev/null || true
            fi
        elif command -v grep &>/dev/null; then
            grep -rl "$query" \
                "$NM_MAILDIR/incoming/" \
                "$NM_MAILDIR/archive/" \
                "$NM_MAILDIR/sent/" 2>/dev/null || true
        else
            echo "notmuch_search: no search tool available (notmuch, rg, or grep)" >&2
            return 1
        fi
    fi
}

# ---------------------------------------------------------------------------
# Count
# ---------------------------------------------------------------------------

notmuch_count() {
    local query="$1"
    if notmuch_available; then
        notmuch count "$query" 2>/dev/null
    else
        # Very rough: count files matching query via grep -l | wc -l
        notmuch_search "$query" --output=files | wc -l
    fi
}

# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

# notmuch_tag <operation><tag> <id...>
notmuch_tag() {
    local op_tag="$1"
    shift

    if notmuch_available; then
        for id in "$@"; do
            notmuch tag "$op_tag" -- "id:$id" 2>/dev/null || true
        done
    else
        if [[ -n "${NM_VERBOSE:-}" ]]; then
            echo "notmuch_tag: notmuch not available, skipping tag $op_tag" >&2
        fi
    fi
}

# ---------------------------------------------------------------------------
# Index new mail
# ---------------------------------------------------------------------------

notmuch_new() {
    if notmuch_available; then
        notmuch new 2>/dev/null
    fi
}

# ---------------------------------------------------------------------------
# Resolve ID to path via notmuch
# ---------------------------------------------------------------------------

notmuch_resolve() {
    local id="$1"
    if notmuch_available; then
        notmuch search --output=files "id:$id" 2>/dev/null | head -1
    else
        return 1
    fi
}
