#!/usr/bin/env bash
# maildir.sh — Maildir operations library
#
# Source this: source "${NM_LIBDIR}/maildir.sh"

if ! declare -f log_event &>/dev/null; then
    NM_LIBDIR="${NM_LIBDIR:-$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")}"
    source "${NM_LIBDIR}/common.sh"
fi

# ---------------------------------------------------------------------------
# Maildir path helpers
# ---------------------------------------------------------------------------

# maildir_cur <base> — path to cur/ subdirectory
maildir_cur() { echo "${1}/cur"; }

# maildir_new <base> — path to new/ subdirectory
maildir_new() { echo "${1}/new"; }

# maildir_tmp <base> — path to tmp/ subdirectory
maildir_tmp() { echo "${1}/tmp"; }

# ---------------------------------------------------------------------------
# Move message to Maildir (safe: tmp → new)
# ---------------------------------------------------------------------------

maildir_deliver() {
    local file="$1"
    local maildir="$2"

    local tmpdir newdir
    tmpdir=$(maildir_tmp "$maildir")
    newdir=$(maildir_new "$maildir")

    mkdir -p "$tmpdir" "$newdir"

    local id
    id=$(maildir_new_id)
    local tmp="$tmpdir/$id"

    cp "$file" "$tmp"
    mv "$tmp" "$newdir/$id"  # atomic on same filesystem
    echo "$newdir/$id"
}

# ---------------------------------------------------------------------------
# Flag operations (Maildir info suffix)
# ---------------------------------------------------------------------------

# Maildir flags are in the filename suffix: `:2,<flags>`
# Flags: F=flagged, R=replied, S=seen, T=trashed, D=draft

get_info() {
    local file="$1"
    local basename
    basename="$(basename "$file")"
    if [[ "$basename" == *:2,* ]]; then
        echo "${basename##*:2,}"
    else
        echo ""
    fi
}

set_flags() {
    local file="$1"
    local new_flags="$2"  # e.g., "S" for seen

    local dir
    dir=$(dirname "$file")
    local basename
    basename=$(basename "$file")

    # Remove existing info part
    local stem="${basename%%:2,*}"

    local newname="$dir/${stem}:2,${new_flags}"

    if [[ "$file" != "$newname" ]]; then
        mv "$file" "$newname"
        echo "$newname"
    else
        echo "$file"
    fi
}

# add_flag <file> <flag> — add a single flag
add_flag() {
    local file="$1"
    local flag="$2"
    local cur
    cur=$(get_info "$file")

    if [[ "$cur" != *"$flag"* ]]; then
        cur="${cur}${flag}"
        # Sort flags (Maildir convention: alphabetic)
        cur=$(echo "$cur" | fold -w1 | sort | tr -d '\n')
        set_flags "$file" "$cur"
    fi
}

# remove_flag <file> <flag> — remove a single flag
remove_flag() {
    local file="$1"
    local flag="$2"
    local cur
    cur=$(get_info "$file")

    if [[ "$cur" == *"$flag"* ]]; then
        cur="${cur//$flag/}"
        set_flags "$file" "$cur"
    fi
}

# ---------------------------------------------------------------------------
# Move between Maildirs (preserving flags)
# ---------------------------------------------------------------------------

maildir_transfer() {
    local src="$1"
    local dst_maildir="$2"

    if [[ ! -f "$src" ]]; then
        echo "maildir_transfer: not found: $src" >&2
        return 1
    fi

    local id
    id=$(maildir_new_id)
    local dst_cur
    dst_cur=$(maildir_cur "$dst_maildir")

    mkdir -p "$dst_cur"

    local basename="${id}:2,"
    local flags
    flags=$(get_info "$src")
    [[ -n "$flags" ]] && basename="${id}:2,${flags}"

    mv "$src" "$dst_cur/$basename"
    echo "$dst_cur/$basename"
}

# ---------------------------------------------------------------------------
# List messages in a Maildir (sorted by mtime)
# ---------------------------------------------------------------------------

maildir_list() {
    local maildir="$1"
    find "$(maildir_new "$maildir")" "$(maildir_cur "$maildir")" \
        -type f 2>/dev/null | sort
}

# maildir_list_new <maildir>
maildir_list_new() {
    local maildir="$1"
    find "$(maildir_new "$maildir")" -type f 2>/dev/null | sort
}

# ---------------------------------------------------------------------------
# Message counts
# ---------------------------------------------------------------------------

maildir_stats() {
    local maildir="$1"
    local new cur
    new=$(find "$(maildir_new "$maildir")" -type f 2>/dev/null | wc -l)
    cur=$(find "$(maildir_cur "$maildir")" -type f 2>/dev/null | wc -l)
    echo "$new $cur"
}

# maildir_total <maildir> — total messages (new + cur)
maildir_total() {
    local stats
    stats=$(maildir_stats "$1")
    echo $(( $(echo "$stats" | awk '{print $1}') + $(echo "$stats" | awk '{print $2}') ))
}
