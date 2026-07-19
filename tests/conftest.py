"""Shared fixtures for nmail tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmail.config import Config
from nmail.constants import (
    MAILDIR_SUBDIRS,
    MAILDIR_SUBFOLDERS,
    NM_CONFIG_HOME,
    NM_MAILDIR,
)


@pytest.fixture
def maildir_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a full Maildir tree under tmp_path and point Config.maildir at it."""
    base = tmp_path / "Mail"
    for subdir in MAILDIR_SUBDIRS:
        for sf in MAILDIR_SUBFOLDERS:
            (base / subdir / sf).mkdir(parents=True)
    monkeypatch.setattr(Config, "maildir", property(lambda _: base))
    return base


@pytest.fixture
def config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point NM_CONFIG_HOME at a temp dir."""
    cfg_home = tmp_path / ".config" / "nmail"
    cfg_home.mkdir(parents=True)
    import nmail.constants

    monkeypatch.setattr(nmail.constants, "NM_CONFIG_HOME", cfg_home)
    return cfg_home


@pytest.fixture
def patched_config(monkeypatch: pytest.MonkeyPatch, maildir_tree: Path) -> Config:
    """Return a Config singleton whose maildir and config_home are patched.

    Also patches the module-level _config in nmail.config so get_config()
    returns this instance everywhere. Resets _data so each test gets fresh config.
    """
    import nmail.config

    cfg = Config()
    cfg._data = None  # force fresh load each test
    monkeypatch.setattr(nmail.config, "_config", cfg)
    return cfg


@pytest.fixture
def sample_mail(maildir_tree: Path) -> Path:
    """Create a minimal RFC5322 mail file in incoming/new."""
    msg = maildir_tree / "incoming" / "new" / "1712345678.M123456P1234.localhost"
    msg.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Test message\n"
        "Date: Mon, 01 Jan 2024 12:00:00 +0000\n"
        "Message-ID: <abc123@example.com>\n"
        "MIME-Version: 1.0\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "Hello Bob,\n"
        "This is a test.\n"
    )
    return msg


@pytest.fixture
def sample_mail_with_flags(maildir_tree: Path) -> Path:
    """Create a mail in incoming/cur with Seen and Flagged flags."""
    msg = maildir_tree / "incoming" / "cur" / "1712345678.M123456P1234.localhost:2,FS"
    msg.write_text(
        "From: Charlie <charlie@example.com>\n"
        "To: Dave <dave@example.com>\n"
        "Subject: Flagged and seen\n"
        "Date: Mon, 01 Jan 2024 13:00:00 +0000\n"
        "\n"
        "Important message.\n"
    )
    return msg


@pytest.fixture
def draft_file(maildir_tree: Path) -> Path:
    """Create a valid draft.md in drafts/."""
    draft = maildir_tree / "drafts" / "20240101-120000.md"
    draft.write_text(
        "From: alice@example.com\nTo: bob@example.com\nSubject: Hello\n\n---\n\nHello **world**\n"
    )
    return draft


@pytest.fixture
def queue_msg(maildir_tree: Path) -> Path:
    """A rendered MIME message in queue/new/ ready to send."""
    msg = maildir_tree / "queue" / "new" / "20240101-120000.md"
    msg.write_text(
        "From: alice@example.com\nTo: bob@example.com\nSubject: Queued\n\n---\n\nSend me.\n"
    )
    return msg
