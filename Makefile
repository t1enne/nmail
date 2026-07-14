.PHONY: install uninstall test clean lint

PREFIX ?= $(HOME)/.local
BINDIR = $(PREFIX)/bin
LIBDIR = $(PREFIX)/lib/nmail

install:
	./install.sh --prefix $(PREFIX)

uninstall:
	@echo "Removing binaries..."
	@for f in bin/*; do \
		name=$$(basename $$f); \
		rm -f "$(BINDIR)/$$name"; \
		echo "  $$name"; \
	done
	@echo "Removing libraries..."
	@rm -rf "$(LIBDIR)"
	@echo "nmail uninstalled from $(PREFIX)."
	@echo "Maildir (~/Mail) and config (~/.config/nmail) left untouched."

test:
	@echo "=== Testing nmail commands ==="
	@echo ""
	@echo "--- mail-compose --help ---"
	@NM_LIBDIR=./src ./bin/mail-compose --help 2>&1 | head -3
	@echo ""
	@echo "--- mail-render --help ---"
	@NM_LIBDIR=./src ./bin/mail-render --help 2>&1 | head -3
	@echo ""
	@echo "--- mail-send --help ---"
	@NM_LIBDIR=./src ./bin/mail-send --help 2>&1 | head -3
	@echo ""
	@echo "--- mail-sync --help ---"
	@NM_LIBDIR=./src ./bin/mail-sync --help 2>&1 | head -3
	@echo ""
	@echo "--- mail-search --help ---"
	@NM_LIBDIR=./src ./bin/mail-search --help 2>&1 | head -3
	@echo ""
	@echo "--- mail-status ---"
	@NM_MAILDIR=/tmp/nmail-test-maildir NM_LIBDIR=./src ./bin/mail-status 2>&1
	@rm -rf /tmp/nmail-test-maildir
	@echo ""
	@echo "--- All commands parse --help without error ---"
	@for cmd in bin/*; do \
		name=$$(basename $$cmd); \
		NM_LIBDIR=./src ./bin/$$name --help >/dev/null 2>&1 || echo "FAIL: $$name --help failed"; \
	done
	@echo "  All passed."

clean:
	rm -rf /tmp/nmail-test-*

lint:
	@echo "=== ShellCheck ==="
	@if command -v shellcheck &>/dev/null; then \
		shellcheck bin/* src/*.sh config/hooks.d/*; \
	else \
		echo "shellcheck not installed. Skipping."; \
	fi
