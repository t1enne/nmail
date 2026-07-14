#!/usr/bin/env bash
# install.sh — install nmail into the user's environment
#
# Usage: ./install.sh [--prefix ~/.local]

set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
BINDIR="$PREFIX/bin"
LIBDIR="$PREFIX/lib/nmail"
CONFIGDIR="${XDG_CONFIG_HOME:-$HOME/.config}/nmail"
MAILDIR="$HOME/Mail"
STATEDIR="${XDG_STATE_HOME:-$HOME/.local/state}/nmail"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)   PREFIX="$2"; BINDIR="$PREFIX/bin"; LIBDIR="$PREFIX/lib/nmail"; shift 2 ;;
        --prefix=*) PREFIX="${1#*=}"; BINDIR="$PREFIX/bin"; LIBDIR="$PREFIX/lib/nmail"; shift ;;
        -h|--help)
            echo "Usage: ./install.sh [--prefix ~/.local]"
            echo ""
            echo "Installs nmail commands to \$PREFIX/bin and libraries to \$PREFIX/lib/nmail"
            echo "Copies config to ~/.config/nmail/ (if not exists)"
            echo "Creates ~/Mail/ directory structure"
            exit 0
            ;;
        *) shift ;;
    esac
done

echo "=== nmail install ==="
echo "  Prefix:   $PREFIX"
echo "  Bin dir:  $BINDIR"
echo "  Lib dir:  $LIBDIR"
echo "  Config:   $CONFIGDIR"
echo "  Maildir:  $MAILDIR"
echo ""

# ---------------------------------------------------------------------------
# Create directories
# ---------------------------------------------------------------------------

mkdir -p "$BINDIR" "$LIBDIR" "$CONFIGDIR/hooks.d"

# ---------------------------------------------------------------------------
# Install binaries
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing binaries..."
for script in "$SCRIPT_DIR/bin/"*; do
    name=$(basename "$script")
    if [[ -x "$script" ]]; then
        # Create wrapper that sets NM_LIBDIR
        cat > "$BINDIR/$name" <<WRAPPER
#!/usr/bin/env bash
export NM_LIBDIR="$LIBDIR"
exec "$SCRIPT_DIR/bin/$name" "\$@"
WRAPPER
        chmod +x "$BINDIR/$name"
        echo "  $name"
    fi
done

# ---------------------------------------------------------------------------
# Install libraries
# ---------------------------------------------------------------------------

echo "Installing libraries..."
for lib in "$SCRIPT_DIR/src/"*.sh; do
    name=$(basename "$lib")
    cp "$lib" "$LIBDIR/$name"
    echo "  $name"
done

# ---------------------------------------------------------------------------
# Install config (don't overwrite existing)
# ---------------------------------------------------------------------------

if [[ -f "$CONFIGDIR/config.toml" ]]; then
    echo "Config exists: $CONFIGDIR/config.toml (not overwritten)"
else
    cp "$SCRIPT_DIR/config/config.toml" "$CONFIGDIR/config.toml"
    echo "Config: $CONFIGDIR/config.toml"
fi

# ---------------------------------------------------------------------------
# Install hooks (don't overwrite existing)
# ---------------------------------------------------------------------------

for hook in "$SCRIPT_DIR/config/hooks.d/"*; do
    name=$(basename "$hook")
    if [[ -f "$CONFIGDIR/hooks.d/$name" ]]; then
        echo "Hook exists: $name (not overwritten)"
    else
        cp "$hook" "$CONFIGDIR/hooks.d/$name"
        chmod +x "$CONFIGDIR/hooks.d/$name"
        echo "Hook: $name"
    fi
done

# ---------------------------------------------------------------------------
# Create Maildir structure
# ---------------------------------------------------------------------------

echo "Creating Maildir structure..."
for d in \
    incoming/cur incoming/new incoming/tmp \
    archive/cur \
    drafts \
    sent/cur sent/new sent/tmp \
    trash/cur trash/new trash/tmp \
    attachments \
    queue/cur queue/new queue/tmp \
    templates \
    logs; do
    mkdir -p "$MAILDIR/$d"
done

mkdir -p "$STATEDIR"

# Copy default templates if not present
for tmpl in "$SCRIPT_DIR/templates/"*.md; do
    name=$(basename "$tmpl")
    if [[ ! -f "$MAILDIR/templates/$name" ]]; then
        cp "$tmpl" "$MAILDIR/templates/$name"
        echo "Template: $name"
    fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Ensure $BINDIR is in your PATH"
echo "     export PATH=\"$BINDIR:\$PATH\""
echo ""
echo "  2. Edit config: $EDITOR $CONFIGDIR/config.toml"
echo ""
echo "  3. Configure msmtp: $EDITOR ~/.msmtprc"
echo ""
echo "  4. Configure mbsync: $EDITOR ~/.mbsyncrc"
echo ""
echo "  5. Sync mail: mail-sync"
echo ""
echo "  6. Launch workspace: mail-session"
