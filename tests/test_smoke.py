"""Smoke tests for core nmail library — no external tools required."""

from __future__ import annotations

from pathlib import Path

from nmail.config import Config
from nmail.constants import MAILDIR_SUBDIRS, MAILDIR_SUBFOLDERS
from nmail.drafts import validate_draft
from nmail.headers import extract_body, extract_header
from nmail.maildir import (
    add_flag,
    has_flag,
    maildir_count,
    maildir_new_id,
    maildir_transfer,
    remove_flag,
)
from nmail.render import DraftParts, parse_draft, render_message


def test_maildir_new_id_is_unique() -> None:
    ids = {maildir_new_id(pid=i) for i in range(100)}
    assert len(ids) == 100


def test_maildir_flag_operations(tmp_path: Path) -> None:
    f = tmp_path / "1712345678.M123456P1234.localhost"
    f.write_text("test")

    flagged = add_flag(f, "seen")
    assert has_flag(flagged, "seen")
    assert "S" in flagged.name

    unflagged = remove_flag(flagged, "seen")
    assert not has_flag(unflagged, "seen")
    assert "S" not in unflagged.name


def test_maildir_flag_map(tmp_path: Path) -> None:
    f = tmp_path / "1712345678.M123456P1234.localhost"
    f.write_text("test")
    flagged = add_flag(f, "flagged")
    assert "F" in flagged.name

    f2 = tmp_path / "1712345678.M123456P1234.otherhost"
    f2.write_text("test")
    replied = add_flag(f2, "replied")
    assert "R" in replied.name


def test_maildir_count(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / "test" / "new"
    d.mkdir(parents=True)
    (d / "msg1").write_text("x")
    (d / "msg2").write_text("y")

    from nmail.maildir import maildir_count as _count

    import nmail.config

    cfg = Config()
    monkeypatch.setattr(Config, "maildir", property(lambda self: tmp_path))
    monkeypatch.setattr(nmail.config, "_config", cfg)
    assert _count("test") == 2


def test_parse_draft_simple() -> None:
    draft = "From: alice@x.com\nTo: bob@x.com\nSubject: Hi\n\n---\n\nHello world"
    d = Path("test.md")
    d.write_text(draft)
    parts = parse_draft(d)
    assert parts.headers == "From: alice@x.com\nTo: bob@x.com\nSubject: Hi"
    assert parts.body == "Hello world"
    d.unlink()


def test_parse_draft_with_attachments() -> None:
    draft = "From: a\nTo: b\nSubject: c\n\n---\n\nbody\n\n---\nfile1.pdf\nfile2.pdf"
    d = Path("test2.md")
    d.write_text(draft)
    parts = parse_draft(d)
    assert "file1.pdf" in parts.attachments
    assert "file2.pdf" in parts.attachments
    d.unlink()


def test_parse_draft_no_headers() -> None:
    d = Path("nodash.md")
    d.write_text("Just a body, no headers")
    parts = parse_draft(d)
    assert parts.headers == ""
    assert parts.body == "Just a body, no headers"
    d.unlink()


def test_render_message_plain() -> None:
    draft = "From: a@x.com\nTo: b@x.com\nSubject: Test\n\n---\n\nHello **world**"
    d = Path("render_test.md")
    d.write_text(draft)
    result = render_message(d, "plain")
    assert "Hello world" in result
    assert "From: a@x.com" in result
    d.unlink()


def test_render_message_mime() -> None:
    draft = "From: a@x.com\nTo: b@x.com\nSubject: Test\n\n---\n\nHello"
    d = Path("render_mime.md")
    d.write_text(draft)
    result = render_message(d, "mime")
    assert "multipart/alternative" in result
    assert "Hello" in result
    d.unlink()


def test_extract_header() -> None:
    f = Path("hdr_test.txt")
    f.write_text("From: alice@x.com\nTo: bob@x.com\nSubject: Hi\n\nBody here")
    assert extract_header(f, "From") == "alice@x.com"
    assert extract_header(f, "Subject") == "Hi"
    assert extract_header(f, "X-Nonexist") is None
    f.unlink()


def test_extract_body() -> None:
    f = Path("body_test.txt")
    f.write_text("From: a\nTo: b\nSubject: c\n\nHello\nWorld")
    assert extract_body(f) == "Hello\nWorld"
    f.unlink()


def test_draft_validate() -> None:
    d = Path("validate_test.md")
    d.write_text("From: a\nTo: b@x.com\nSubject: Hi\n\n---\n\nBody")
    assert validate_draft(d)
    d.unlink()


def test_draft_validate_no_subject() -> None:
    d = Path("validate_no_subj.md")
    d.write_text("From: a\nTo: b@x.com\nSubject:\n\n---\n\nBody")
    assert not validate_draft(d)
    d.unlink()


def test_constants() -> None:
    assert "incoming" in MAILDIR_SUBDIRS
    assert "archive" in MAILDIR_SUBDIRS
    assert "sent" in MAILDIR_SUBDIRS
    assert "trash" in MAILDIR_SUBDIRS
    assert "new" in MAILDIR_SUBFOLDERS
    assert "cur" in MAILDIR_SUBFOLDERS
    assert "tmp" in MAILDIR_SUBFOLDERS
