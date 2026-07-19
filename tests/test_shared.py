"""Tests for src/nmail/shared.py — shared CLI utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmail.config import Config
from nmail.shared import _detect_profile


class TestDetectProfile:
    """Coverage for _detect_profile: flat mode, multi-profile, edge cases."""

    def test_flat_mode_returns_empty(self, patched_config: Config, maildir_tree: Path) -> None:
        f = maildir_tree / "incoming" / "new" / "msg1"
        assert _detect_profile(f, patched_config) == ""

    def test_multi_profile_detects_correct_profile(
        self, patched_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Config, "profiles", property(lambda _: ["work", "personal"]))
        f = patched_config.maildir / "work" / "incoming" / "new" / "msg1"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
        assert _detect_profile(f, patched_config) == "work"

    def test_multi_profile_second_profile(
        self, patched_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Config, "profiles", property(lambda _: ["work", "personal"]))
        f = patched_config.maildir / "personal" / "sent" / "cur" / "msg2"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
        assert _detect_profile(f, patched_config) == "personal"

    def test_path_outside_maildir_returns_empty(
        self, patched_config: Config
    ) -> None:
        assert _detect_profile(Path("/tmp/random_msg"), patched_config) == ""

    def test_nested_in_subsubfolder_returns_empty(
        self, patched_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Config, "profiles", property(lambda _: ["work"]))
        # Path is inside maildir but not deep enough to have profile/subdir/new|cur/msg
        f = patched_config.maildir / "work" / "orphan_msg"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
        # profile detected (parts[0] is 'work' and parts length >= 3? parts=['work','orphan_msg'] → len=2)
        # Correction: relative_to gives 'work/orphan_msg', split → ['work','orphan_msg'], len=2 < 3 → ""
        assert _detect_profile(f, patched_config) == ""

    def test_deeply_nested_still_works(
        self, patched_config: Config, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Config, "profiles", property(lambda _: ["work"]))
        f = patched_config.maildir / "work" / "incoming" / "new" / "sub" / "msg3"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()
        assert _detect_profile(f, patched_config) == "work"
