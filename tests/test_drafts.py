"""Tests for src/nmail/drafts.py — draft creation, validation, queueing."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmail.config import Config
from nmail.drafts import create_draft, queue_draft, validate_draft

# ── create_draft ─────────────────────────────────────────────────────────────


def test_create_draft_default(
    maildir_tree: Path,
    patched_config: Config,
) -> None:
    draft = create_draft()
    assert draft.exists()
    assert draft.suffix == ".md"
    assert draft.parent == maildir_tree / "drafts"
    content = draft.read_text()
    assert "From:" in content
    assert "To:" in content
    assert "Subject:" in content


def test_create_draft_with_fields(
    maildir_tree: Path,
    patched_config: Config,
) -> None:
    draft = create_draft(to="bob@example.com", subject="Hello", cc="cc@x.com", bcc="bcc@x.com")
    content = draft.read_text()
    assert "To: bob@example.com" in content
    assert "Subject: Hello" in content
    assert "Cc: cc@x.com" in content
    assert "Bcc: bcc@x.com" in content


def test_create_draft_from_template(
    maildir_tree: Path,
    patched_config: Config,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a template file exists, use it."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "reply.md").write_text("From: \nTo: \nCc: \nSubject: Re: \nIn-Reply-To: \n\n")

    # Patch the Config class property so create_draft finds our template dir

    monkeypatch.setattr(Config, "templates_dir", property(lambda _self: templates_dir))

    draft = create_draft(template="reply", to="bob@x.com")
    content = draft.read_text()
    assert "In-Reply-To:" in content
    assert "To: bob@x.com" in content


def test_create_draft_template_not_found_falls_back(
    maildir_tree: Path,
    patched_config: Config,
) -> None:
    """Missing template → default inline template."""
    draft = create_draft(template="nonexistent")
    content = draft.read_text()
    assert "From:" in content


def test_create_draft_unique_names(maildir_tree: Path, patched_config: Config) -> None:
    """Each call produces a unique filename (timestamp-based)."""
    import time

    d1 = create_draft()
    time.sleep(1.1)
    d2 = create_draft()
    assert d1.name != d2.name


# ── validate_draft ───────────────────────────────────────────────────────────


def test_validate_draft_valid(draft_file: Path) -> None:
    assert validate_draft(draft_file)


def test_validate_draft_missing_to(maildir_tree: Path) -> None:
    d = maildir_tree / "drafts" / "no_to.md"
    d.write_text("From: a@x.com\nSubject: Hi\n\n---\n\nBody")
    assert not validate_draft(d)


def test_validate_draft_missing_subject(maildir_tree: Path) -> None:
    d = maildir_tree / "drafts" / "no_subj.md"
    d.write_text("From: a@x.com\nTo: b@x.com\n\n---\n\nBody")
    assert not validate_draft(d)


def test_validate_draft_empty_to(maildir_tree: Path) -> None:
    d = maildir_tree / "drafts" / "empty_to.md"
    d.write_text("From: a@x.com\nTo: \nSubject: Hi\n\n---\n\nBody")
    assert not validate_draft(d)


def test_validate_draft_empty_subject(maildir_tree: Path) -> None:
    d = maildir_tree / "drafts" / "empty_subj.md"
    d.write_text("From: a@x.com\nTo: b@x.com\nSubject:\n\n---\n\nBody")
    assert not validate_draft(d)


def test_validate_draft_no_headers() -> None:
    d = Path("noheaders.md")
    d.write_text("Just body text")
    assert not validate_draft(d)
    d.unlink()


# ── queue_draft ──────────────────────────────────────────────────────────────


def test_queue_draft_moves_to_queue_new(
    maildir_tree: Path,
    draft_file: Path,
    patched_config: Config,
) -> None:
    dest = queue_draft(draft_file)
    assert dest.parent.name == "new"
    assert dest.parent.parent.name == "queue"
    assert not draft_file.exists()
    assert dest.exists()


def test_queue_draft_preserves_content(
    maildir_tree: Path,
    draft_file: Path,
    patched_config: Config,
) -> None:
    original = draft_file.read_text()
    dest = queue_draft(draft_file)
    assert dest.read_text() == original


# ── _atomic_write (implicitly tested via create_draft) ───────────────────────


def test_atomic_write_no_tmp_left_behind(
    maildir_tree: Path,
    patched_config: Config,
) -> None:
    draft = create_draft()
    # Check no .tmp left behind
    tmp_files = list(draft.parent.glob("*.tmp"))
    assert len(tmp_files) == 0
