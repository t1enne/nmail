"""Tests for src/nmail/maildir.py — Maildir operations.

Covers: flag manipulation, counting, listing, transfer, mark_read,
ensure_maildir, maildir_new_id uniqueness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nmail.maildir import (
    add_flag,
    ensure_maildir,
    has_flag,
    maildir_count,
    maildir_list_all,
    maildir_list_new,
    maildir_move,
    maildir_new_id,
    maildir_total,
    maildir_transfer,
    mark_read,
    remove_flag,
)

# ── maildir_new_id ───────────────────────────────────────────────────────────


def test_maildir_new_id_format() -> None:
    mid = maildir_new_id(host="testhost", pid=42)
    assert ".M" in mid
    assert "P42" in mid
    assert mid.endswith(".testhost")


def test_maildir_new_id_unique_batch() -> None:
    ids = {maildir_new_id(pid=i) for i in range(1000)}
    assert len(ids) == 1000


# ── ensure_maildir ───────────────────────────────────────────────────────────


def test_ensure_maildir_creates_structure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "FreshMail"
    import nmail.config
    from nmail.config import Config

    cfg = Config()
    monkeypatch.setattr(Config, "maildir", property(lambda self: base))
    monkeypatch.setattr(nmail.config, "_config", cfg)

    ensure_maildir()

    from nmail.constants import MAILDIR_SUBDIRS, MAILDIR_SUBFOLDERS

    for subdir in MAILDIR_SUBDIRS:
        for sf in MAILDIR_SUBFOLDERS:
            assert (base / subdir / sf).is_dir()


# ── maildir_move ─────────────────────────────────────────────────────────────


def test_maildir_move_basic(maildir_tree: Path, sample_mail: Path) -> None:
    dest = maildir_move(sample_mail, "archive")
    assert dest.parent.name == "new"
    assert dest.parent.parent.name == "archive"
    assert not sample_mail.exists()
    assert dest.exists()


def test_maildir_move_atomic(maildir_tree: Path, sample_mail: Path) -> None:
    """os.rename on same filesystem is atomic — file should never be at both
    locations or neither."""
    content = sample_mail.read_text()
    dest = maildir_move(sample_mail, "archive")
    assert dest.read_text() == content
    assert not sample_mail.exists()


# ── Flag operations ──────────────────────────────────────────────────────────


def test_add_flag_seen(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    result = add_flag(f, "seen")
    assert "S" in result.name
    assert has_flag(result, "seen")


def test_add_flag_flagged(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    result = add_flag(f, "flagged")
    assert "F" in result.name


def test_add_flag_replied(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    result = add_flag(f, "replied")
    assert "R" in result.name


def test_add_flag_trashed(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    result = add_flag(f, "trashed")
    assert "T" in result.name


def test_add_flag_draft(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    result = add_flag(f, "draft")
    assert "D" in result.name


def test_add_flag_multiple(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    f = add_flag(f, "seen")
    f = add_flag(f, "flagged")
    f = add_flag(f, "replied")
    assert has_flag(f, "seen")
    assert has_flag(f, "flagged")
    assert has_flag(f, "replied")
    # Flags should be sorted
    assert "FRS" in f.name or _flag_suffix_for(f) == "FRS"


def test_remove_flag(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    f = add_flag(f, "seen")
    f = add_flag(f, "flagged")
    assert has_flag(f, "seen")
    f = remove_flag(f, "seen")
    assert not has_flag(f, "seen")
    assert has_flag(f, "flagged")


def test_remove_last_flag_clears_suffix(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    f = add_flag(f, "seen")
    f = remove_flag(f, "seen")
    assert ":2," not in f.name


def test_has_flag_none(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    assert not has_flag(f, "seen")
    assert not has_flag(f, "flagged")


def test_add_flag_raw_code(maildir_tree: Path) -> None:
    """If a flag isn't in FLAG_MAP, the code itself is used."""
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    result = add_flag(f, "X")
    assert "X" in result.name
    assert has_flag(result, "X")


def test_add_flag_idempotent(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "msg"
    f.write_text("test")
    f1 = add_flag(f, "seen")
    f2 = add_flag(f1, "seen")
    assert f1 == f2


# ── mark_read ────────────────────────────────────────────────────────────────


def test_mark_read_moves_new_to_cur(maildir_tree: Path, sample_mail: Path) -> None:
    assert sample_mail.parent.name == "new"
    result = mark_read(sample_mail)
    assert result.parent.name == "cur"
    assert has_flag(result, "seen")
    assert not sample_mail.exists()


def test_mark_read_already_in_cur(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "cur" / "already_cur"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("test")
    result = mark_read(f)
    assert has_flag(result, "seen")


def test_mark_read_nonexistent_file(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "new" / "does_not_exist"
    result = mark_read(f)
    assert result == f


# ── maildir_count / maildir_total ────────────────────────────────────────────


def test_maildir_count_empty(maildir_tree: Path) -> None:
    assert maildir_count("incoming") == 0


def test_maildir_count_with_messages(maildir_tree: Path) -> None:
    (maildir_tree / "incoming" / "new" / "msg1").write_text("a")
    (maildir_tree / "incoming" / "new" / "msg2").write_text("b")
    (maildir_tree / "incoming" / "cur" / "msg3").write_text("c")
    assert maildir_count("incoming") == 3


def test_maildir_count_new_only(maildir_tree: Path) -> None:
    (maildir_tree / "incoming" / "new" / "msg1").write_text("a")
    assert maildir_count("incoming") == 1


def test_maildir_count_cur_only(maildir_tree: Path) -> None:
    (maildir_tree / "incoming" / "cur" / "msg1").write_text("a")
    assert maildir_count("incoming") == 1


def test_maildir_total_alias(maildir_tree: Path) -> None:
    (maildir_tree / "archive" / "new" / "x").write_text("x")
    assert maildir_total("archive") == 1


# ── maildir_list_new ─────────────────────────────────────────────────────────


def test_maildir_list_new_returns_sorted(maildir_tree: Path) -> None:
    (maildir_tree / "incoming" / "new" / "a").write_text("1")
    (maildir_tree / "incoming" / "new" / "b").write_text("2")
    result = maildir_list_new("incoming")
    assert len(result) == 2
    assert result[0].stat().st_mtime >= result[1].stat().st_mtime  # reverse mtime


def test_maildir_list_new_missing_dir(maildir_tree: Path) -> None:
    assert maildir_list_new("nonexistent") == []


# ── maildir_list_all ─────────────────────────────────────────────────────────


def test_maildir_list_all(maildir_tree: Path) -> None:
    (maildir_tree / "archive" / "new" / "n1").write_text("n")
    (maildir_tree / "archive" / "cur" / "c1").write_text("c")
    result = maildir_list_all("archive")
    assert len(result) == 2


def test_maildir_list_all_empty(maildir_tree: Path) -> None:
    assert maildir_list_all("sent") == []


# ── maildir_transfer ─────────────────────────────────────────────────────────


def test_maildir_transfer_preserves_flags(maildir_tree: Path) -> None:
    f = maildir_tree / "incoming" / "cur" / "flagged_msg"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("test")
    f = add_flag(f, "flagged")
    f = add_flag(f, "seen")

    dest = maildir_transfer(f, "archive")
    assert has_flag(dest, "flagged")
    assert has_flag(dest, "seen")
    assert not f.exists()


def test_maildir_transfer_no_flags(maildir_tree: Path, sample_mail: Path) -> None:
    assert not has_flag(sample_mail, "seen")
    dest = maildir_transfer(sample_mail, "archive")
    assert not has_flag(dest, "seen")
    assert dest.exists()


# ── helpers ──────────────────────────────────────────────────────────────────


def _flag_suffix_for(path: Path) -> str:
    import re

    m = re.search(r":2,([A-Z]*)$", path.name)
    return m.group(1) if m else ""
