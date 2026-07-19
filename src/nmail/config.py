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
    MAILDIR_SUBDIRS,
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
        # Check env first, then top-level maildir, then default
        env_val = os.environ.get("NM_MAILDIR")
        if env_val:
            return Path(env_val).expanduser()
        top_val = self._cfg.get("maildir")
        if top_val:
            return Path(top_val).expanduser()
        gen_val = self._cfg.get("general", {}).get("maildir")
        if gen_val:
            return Path(gen_val).expanduser()
        return NM_MAILDIR

    @property
    def profiles(self) -> list[str]:
        """List of configured profile names."""
        pcfg = self._cfg.get("profiles", {})
        # Only keys with dict values are profile tables (not the 'default' key)
        return [k for k, v in pcfg.items() if isinstance(v, dict)]

    @property
    def profile(self) -> str | None:
        """Active profile (NM_PROFILE env, config default, or None for flat mode)."""
        env = os.environ.get("NM_PROFILE")
        if env:
            return env
        pcfg = self._cfg.get("profiles", {})
        default_val = pcfg.get("default", None) if isinstance(pcfg, dict) else None
        if isinstance(default_val, str) and default_val:
            return default_val
        return None

    def profile_path(self, profile: str, subdir: str = "") -> Path:
        """Resolve a profile's maildir path.

        ~/Mail/<profile>/<subdir> when profile is set.
        ~/Mail/<subdir> when profile is empty (flat / backward compat).
        """
        base = self.maildir
        if profile:
            base = base / profile
        if subdir:
            base = base / subdir
        return base

    def profile_subdirs(self, profile: str) -> list[Path]:
        """All standard subdir paths for a profile."""
        base = self.maildir / profile if profile else self.maildir
        return [base / d for d in MAILDIR_SUBDIRS]

    def all_maildir_files(self) -> list[str]:
        """List all mail files across all profiles (flat or multi-profile)."""
        from .maildir import maildir_list_all

        files: list[str] = []
        profiles = self.profiles if self.profiles else [""]
        for prof in profiles:
            for d in MAILDIR_SUBDIRS:
                path_key = f"{prof}/{d}" if prof else d
                for p in maildir_list_all(path_key):
                    files.append(str(p))
        return files

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
