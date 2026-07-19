"""Tests for src/nmail/config.py — configuration loading and env overrides.

Key insight: from .constants import NM_CONFIG_HOME copies the reference.
Patch nmail.config.NM_CONFIG_HOME (not nmail.constants) to redirect _load().
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nmail.config import Config
from nmail.constants import (
    DEFAULT_PAGER,
    DEFAULT_SMTP_CMD,
    DEFAULT_SYNC_INTERVAL,
    DEFAULT_SYNC_TOOL,
)


@pytest.fixture
def config_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Write a minimal config.toml and point Config._load() at it."""
    nm_dir = tmp_path / ".config" / "nmail"
    nm_dir.mkdir(parents=True)
    toml_path = nm_dir / "config.toml"
    import nmail.config

    monkeypatch.setattr(nmail.config, "NM_CONFIG_HOME", nm_dir)
    monkeypatch.setattr(nmail.config, "NM_MAILDIR", tmp_path / "Mail")
    return toml_path


@pytest.fixture
def fresh_config(config_toml: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """Config singleton cleared, pointing at the test config.toml dir."""
    import nmail.config

    nmail.config._config = None
    cfg = Config()
    monkeypatch.setattr(nmail.config, "_config", cfg)
    return cfg


# ── Defaults ─────────────────────────────────────────────────────────────────


def test_config_defaults_no_config_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no config.toml, all values are defaults."""
    import nmail.config

    empty_dir = tmp_path / "empty_config"
    empty_dir.mkdir()
    monkeypatch.setattr(nmail.config, "NM_CONFIG_HOME", empty_dir)
    monkeypatch.setattr(nmail.config, "NM_MAILDIR", tmp_path / "Mail")
    nmail.config._config = None

    cfg = Config()
    monkeypatch.setattr(nmail.config, "_config", cfg)
    assert cfg.smtp_cmd == DEFAULT_SMTP_CMD
    assert cfg.pager == DEFAULT_PAGER
    assert cfg.sync_tool == DEFAULT_SYNC_TOOL
    assert cfg.sync_interval == DEFAULT_SYNC_INTERVAL
    assert cfg.notmuch_command == "notmuch"
    assert cfg.notmuch_enabled is True


# ── config.toml loading ──────────────────────────────────────────────────────


def test_config_loads_smtp(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[smtp]\ncommand = "msmtp -a custom -t"\n')
    fresh_config._data = None
    assert fresh_config.smtp_cmd == "msmtp -a custom -t"


def test_config_loads_notmuch(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[notmuch]\nenabled = false\ncommand = "/opt/notmuch/bin/notmuch"\n')
    fresh_config._data = None
    assert fresh_config.notmuch_enabled is False
    assert fresh_config.notmuch_command == "/opt/notmuch/bin/notmuch"


def test_config_loads_user_from(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[user]\nfrom = "Me <me@example.com>"\n')
    fresh_config._data = None
    assert fresh_config.from_address == "Me <me@example.com>"


def test_config_loads_maildir(config_toml: Path, fresh_config: Config, tmp_path: Path) -> None:
    custom_mail = str(tmp_path / "MyMail")
    config_toml.write_text(f'maildir = "{custom_mail}"\n')
    fresh_config._data = None
    assert str(fresh_config.maildir) == custom_mail


def test_config_loads_pager(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('pager = "bat"\n')
    fresh_config._data = None
    assert fresh_config.pager == "bat"


def test_config_loads_sync(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[sync]\ntool = "offlineimap"\naccounts = ["work", "personal"]\n')
    fresh_config._data = None
    assert fresh_config.sync_tool == "offlineimap"
    assert fresh_config.sync_accounts == ["work", "personal"]


def test_config_loads_templates_dir(
    config_toml: Path, fresh_config: Config, tmp_path: Path
) -> None:
    tdir = str(tmp_path / "my_templates")
    config_toml.write_text(f'[templates]\ndir = "{tdir}"\n')
    fresh_config._data = None
    assert str(fresh_config.templates_dir) == tdir


def test_config_loads_hooks(config_toml: Path, fresh_config: Config, tmp_path: Path) -> None:
    hdir = str(tmp_path / "hooks")
    config_toml.write_text(f'[hooks]\ndir = "{hdir}"\nenabled = true\n')
    fresh_config._data = None
    assert str(fresh_config.hooks_dir) == hdir


# ── Environment overrides ────────────────────────────────────────────────────


def test_env_override_smtp_cmd(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[smtp]\ncommand = "msmtp -t"\n')
    fresh_config._data = None
    mp = pytest.MonkeyPatch()
    mp.setenv("NM_SMTP_CMD", "sendmail -t")
    assert fresh_config.smtp_cmd == "sendmail -t"
    mp.undo()


def test_env_override_from_address(fresh_config: Config) -> None:
    mp = pytest.MonkeyPatch()
    mp.setenv("NM_FROM", "override@example.com")
    assert fresh_config.from_address == "override@example.com"
    mp.undo()


def test_env_override_pager(fresh_config: Config) -> None:
    mp = pytest.MonkeyPatch()
    mp.setenv("NM_PAGER", "most")
    assert fresh_config.pager == "most"
    mp.undo()


def test_env_override_maildir(fresh_config: Config, tmp_path: Path) -> None:
    mp = pytest.MonkeyPatch()
    mp.setenv("NM_MAILDIR", str(tmp_path / "EnvMail"))
    assert str(fresh_config.maildir) == str(tmp_path / "EnvMail")
    mp.undo()


def test_notmuch_command_from_config(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[notmuch]\ncommand = "/opt/notmuch/bin/notmuch"\n')
    fresh_config._data = None
    assert fresh_config.notmuch_command == "/opt/notmuch/bin/notmuch"


def test_sync_tool_from_config(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text('[sync]\ntool = "offlineimap"\n')
    fresh_config._data = None
    assert fresh_config.sync_tool == "offlineimap"


def test_sync_interval_from_config(config_toml: Path, fresh_config: Config) -> None:
    config_toml.write_text("[sync]\ninterval = 120\n")
    fresh_config._data = None
    assert fresh_config.sync_interval == 120


# ── Config cached ────────────────────────────────────────────────────────────


def test_config_is_cached(fresh_config: Config) -> None:
    _ = fresh_config.smtp_cmd  # trigger load
    assert fresh_config._data is not None
    data_id = id(fresh_config._data)
    _ = fresh_config.pager
    assert id(fresh_config._data) == data_id


# ── editor fallback ──────────────────────────────────────────────────────────


def test_config_editor_default() -> None:
    cfg = Config()
    cfg._data = {}
    editor = cfg.editor
    assert editor == os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))


# ── logging_dir default ──────────────────────────────────────────────────────


def test_config_logging_dir(config_toml: Path, fresh_config: Config) -> None:
    ld = fresh_config.logging_dir
    assert ld.name == "logs"
