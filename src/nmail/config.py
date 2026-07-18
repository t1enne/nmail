"""Configuration: read config.toml, merge with env overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import tomli

from .constants import (
    DEFAULT_PAGER,
    DEFAULT_SMTP_CMD,
    DEFAULT_SYNC_INTERVAL,
    DEFAULT_SYNC_TOOL,
    DEFAULT_TEMPLATE,
    NM_CONFIG_HOME,
    NM_MAILDIR,
)


class Config:
    """Lazy-loaded nmail configuration from config.toml + env."""

    def __init__(self) -> None:
        self._data: dict[str, Any] | None = None

    @property
    def _cfg(self) -> dict[str, Any]:
        if self._data is None:
            self._data = self._load()
        return self._data

    def _load(self) -> dict[str, Any]:
        config_home = Path(os.environ.get("NM_CONFIG_HOME", NM_CONFIG_HOME)).expanduser()
        path = config_home / "config.toml"
        return tomli.loads(path.read_text()) if path.exists() else {}

    # ── simple accessors ─────────────────────────────────────────────────

    @property
    def maildir(self) -> Path:
        return Path(os.environ.get("NM_MAILDIR", self._cfg.get("maildir", NM_MAILDIR))).expanduser()

    @property
    def pager(self) -> str:
        return os.environ.get("NM_PAGER", str(self._cfg.get("pager", DEFAULT_PAGER)))

    @property
    def editor(self) -> str:
        return os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))

    @property
    def smtp_cmd(self) -> str:
        smtp = self._cfg.get("smtp", {}).get("command", DEFAULT_SMTP_CMD)
        return os.environ.get("NM_SMTP_CMD", smtp)

    @property
    def from_address(self) -> str | None:
        return os.environ.get("NM_FROM") or self._cfg.get("user", {}).get("from")

    @property
    def templates_dir(self) -> Path:
        tcfg = self._cfg.get("templates", {})
        return Path(tcfg.get("dir", self.maildir / "templates")).expanduser()

    @property
    def default_template(self) -> str:
        tcfg = self._cfg.get("templates", {})
        return tcfg.get("default", DEFAULT_TEMPLATE)

    @property
    def hooks_dir(self) -> Path | None:
        hcfg = self._cfg.get("hooks", {})
        if hcfg.get("enabled", True):
            return Path(hcfg.get("dir", NM_CONFIG_HOME / "hooks.d")).expanduser()
        return None

    @property
    def logging_dir(self) -> Path:
        lcfg = self._cfg.get("logging", {})
        return Path(lcfg.get("dir", self.maildir / "logs")).expanduser()

    @property
    def log_level(self) -> str:
        return self._cfg.get("logging", {}).get("level", "info")

    @property
    def sync_tool(self) -> str:
        sync = self._cfg.get("sync", {})
        return sync.get("tool", DEFAULT_SYNC_TOOL)

    @property
    def sync_interval(self) -> int:
        return self._cfg.get("sync", {}).get("interval", DEFAULT_SYNC_INTERVAL)

    @property
    def sync_accounts(self) -> list[str]:
        return list(self._cfg.get("sync", {}).get("accounts", []))

    @property
    def notmuch_enabled(self) -> bool:
        return self._cfg.get("notmuch", {}).get("enabled", True)

    @property
    def notmuch_command(self) -> str:
        return self._cfg.get("notmuch", {}).get("command", "notmuch")

    @property
    def notifications_enabled(self) -> bool:
        return self._cfg.get("notifications", {}).get("enabled", True)

    @property
    def notification_events(self) -> list[str]:
        return list(self._cfg.get("notifications", {}).get("events", ["mail:new", "mail:error"]))

    # ── raw access ───────────────────────────────────────────────────────

    def get(self, *keys: str) -> Any:
        node: Any = self._cfg
        for k in keys:
            if isinstance(node, dict):
                node = node.get(k)
            else:
                return None
        return node


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
