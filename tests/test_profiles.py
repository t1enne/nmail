"""Tests for multi-profile behaviour — maildir operations, CLI commands, and path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmail.config import Config
from nmail.constants import MAILDIR_SUBDIRS, MAILDIR_SUBFOLDERS
from nmail.maildir import (
    ensure_maildir,
    maildir_count,
    maildir_list_new,
    maildir_list_all,
    maildir_move,
    maildir_total,
    maildir_transfer,
    mark_read,
)
from nmail.shared import _detect_profile

# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def multi_maildir_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a Maildir tree with two profiles (personal + work)."""
    base = tmp_path / "Mail"
    import nmail.config

    cfg = Config()
    monkeypatch.setattr(Config, "maildir", property(lambda _: base))
    monkeypatch.setattr(Config, "profiles", property(lambda _: ["personal", "work"]))
    monkeypatch.setattr(Config, "profile", property(lambda _: "personal"))
    monkeypatch.setattr(nmail.config, "_config", cfg)

    for prof in ("personal", "work"):
        for subdir in MAILDIR_SUBDIRS:
            for sf in MAILDIR_SUBFOLDERS:
                (base / prof / subdir / sf).mkdir(parents=True)
    return base


@pytest.fixture
def sample_mail_personal(multi_maildir_tree: Path) -> Path:
    """A mail in personal/incoming/new."""
    msg = multi_maildir_tree / "personal" / "incoming" / "new" / "1712345678.M123456P1234.localhost"
    msg.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Personal test\n"
        "Date: Mon, 01 Jan 2024 12:00:00 +0000\n"
        "Message-ID: <personal@example.com>\n"
        "\n"
        "Personal mail.\n"
    )
    return msg


@pytest.fixture
def sample_mail_work(multi_maildir_tree: Path) -> Path:
    """A mail in work/incoming/new."""
    msg = multi_maildir_tree / "work" / "incoming" / "new" / "1712345678.M999999P5678.localhost"
    msg.write_text(
        "From: Boss <boss@company.com>\n"
        "To: Me <me@company.com>\n"
        "Subject: Work test\n"
        "Date: Mon, 01 Jan 2024 13:00:00 +0000\n"
        "Message-ID: <work@company.com>\n"
        "\n"
        "Work mail.\n"
    )
    return msg


# ── ensure_maildir ───────────────────────────────────────────────────────────


def test_ensure_maildir_multi_profile(multi_maildir_tree: Path) -> None:
    """ensure_maildir creates structure for both profiles."""
    # Fixture already called ensure_maildir implicitly via conftest? No — we use
    # multi_maildir_tree which creates dirs manually. Re-run ensure_maildir to
    # test idempotency.
    ensure_maildir()
    for prof in ("personal", "work"):
        for subdir in MAILDIR_SUBDIRS:
            for sf in MAILDIR_SUBFOLDERS:
                assert (multi_maildir_tree / prof / subdir / sf).is_dir()


def test_ensure_maildir_single_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ensure_maildir(profile='work') creates only that profile's structure."""
    base = tmp_path / "Mail"
    import nmail.config
    from nmail.config import Config

    cfg = Config()
    monkeypatch.setattr(Config, "maildir", property(lambda _: base))
    monkeypatch.setattr(Config, "profiles", property(lambda _: ["personal", "work"]))
    monkeypatch.setattr(nmail.config, "_config", cfg)

    ensure_maildir("work")
    # work/ exists
    for subdir in MAILDIR_SUBDIRS:
        for sf in MAILDIR_SUBFOLDERS:
            assert (base / "work" / subdir / sf).is_dir()
    # personal/ does NOT exist
    assert not (base / "personal").exists()


# ── maildir_move ─────────────────────────────────────────────────────────────


def test_maildir_move_profile_subdir(
    multi_maildir_tree: Path, sample_mail_personal: Path
) -> None:
    """maildir_move with 'personal/archive' syntax."""
    dest = maildir_move(sample_mail_personal, "personal/archive")
    assert dest.parent.name == "new"
    assert dest.parent.parent.name == "archive"
    assert dest.parent.parent.parent.name == "personal"
    assert not sample_mail_personal.exists()
    assert dest.exists()


def test_maildir_move_work_profile(
    multi_maildir_tree: Path, sample_mail_work: Path
) -> None:
    """maildir_move with 'work/archive' syntax."""
    dest = maildir_move(sample_mail_work, "work/sent")
    assert dest.parent.parent.parent.name == "work"
    assert dest.parent.parent.name == "sent"


# ── maildir_transfer ─────────────────────────────────────────────────────────


def test_maildir_transfer_across_profiles(
    multi_maildir_tree: Path, sample_mail_personal: Path
) -> None:
    """maildir_transfer to profile-aware destination."""
    dest = maildir_transfer(sample_mail_personal, "personal/archive")
    assert dest.exists()
    assert not sample_mail_personal.exists()
    assert "personal" in str(dest)


# ── maildir_count ────────────────────────────────────────────────────────────


def test_maildir_count_profile_subdir(
    multi_maildir_tree: Path, sample_mail_personal: Path
) -> None:
    """maildir_count('personal/incoming') counts only that profile."""
    assert maildir_count("personal/incoming") == 1
    assert maildir_count("work/incoming") == 0


def test_maildir_count_bare_profile(
    multi_maildir_tree: Path, sample_mail_personal: Path, sample_mail_work: Path
) -> None:
    """maildir_count('personal') sums all subdirs in that profile."""
    # We have 1 in personal/incoming, 1 in work/incoming
    cnt = maildir_count("personal")
    # personal has 1 message (incoming) + 0 elsewhere
    assert cnt >= 1  # only incoming has mail from fixtures


def test_maildir_count_flat_mode(maildir_tree: Path) -> None:
    """maildir_count still works in flat mode."""
    (maildir_tree / "incoming" / "new" / "msg1").write_text("a")
    assert maildir_count("incoming") == 1


# ── maildir_list_new ─────────────────────────────────────────────────────────


def test_maildir_list_new_profile(
    multi_maildir_tree: Path, sample_mail_personal: Path
) -> None:
    result = maildir_list_new("personal/incoming")
    assert len(result) == 1
    assert result[0].name == sample_mail_personal.name


def test_maildir_list_new_flat(maildir_tree: Path, sample_mail: Path) -> None:
    result = maildir_list_new("incoming")
    assert len(result) == 1


# ── maildir_list_all ─────────────────────────────────────────────────────────


def test_maildir_list_all_profile(
    multi_maildir_tree: Path, sample_mail_work: Path
) -> None:
    result = maildir_list_all("work/incoming")
    assert len(result) == 1
    assert result[0].name == sample_mail_work.name


# ── maildir_total ────────────────────────────────────────────────────────────


def test_maildir_total_profile(multi_maildir_tree: Path, sample_mail_personal: Path) -> None:
    assert maildir_total("personal/incoming") == 1


# ── mark_read ────────────────────────────────────────────────────────────────


def test_mark_read_multi_profile(
    multi_maildir_tree: Path, sample_mail_personal: Path
) -> None:
    assert sample_mail_personal.parent.name == "new"
    result = mark_read(sample_mail_personal)
    assert result.parent.name == "cur"
    assert not sample_mail_personal.exists()


# ── _detect_profile ──────────────────────────────────────────────────────────


def test_detect_profile_personal(
    multi_maildir_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import nmail.config
    cfg = nmail.config.get_config()
    f = multi_maildir_tree / "personal" / "archive" / "cur" / "msg"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.touch()
    assert _detect_profile(f, cfg) == "personal"


def test_detect_profile_work(
    multi_maildir_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import nmail.config
    cfg = nmail.config.get_config()
    f = multi_maildir_tree / "work" / "sent" / "new" / "msg"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.touch()
    assert _detect_profile(f, cfg) == "work"


def test_detect_profile_flat(sample_mail: Path, patched_config: Config) -> None:
    assert _detect_profile(sample_mail, patched_config) == ""
