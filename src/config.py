"""Config loader. YAML file + environment variable overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when required configuration is missing or malformed."""


def _normalize_hotkey(s: str) -> str:
    """Lowercase + strip whitespace around tokens.

    The `keyboard` library accepts e.g. 'ctrl+alt+d' but rejects 'Ctrl + Alt + D'.
    We make the config more forgiving by accepting either form.
    """
    return "+".join(part.strip().lower() for part in s.split("+"))


@dataclass
class AIConfig:
    base_url: str
    api_key: str
    model: str


@dataclass
class HotkeyConfig:
    translate: str = "f8"


@dataclass
class LanguageConfig:
    target: str = "zh"


@dataclass
class PopupConfig:
    close_on_focus_lost: bool = True
    pause_close_on_hover: bool = True


@dataclass
class AppConfig:
    autostart: bool = False
    tray: bool = True


@dataclass
class StorageConfig:
    db_path: str = "data/english-helper.db"


@dataclass
class Config:
    ai: AIConfig
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    popup: PopupConfig = field(default_factory=PopupConfig)
    app: AppConfig = field(default_factory=AppConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

    # ---- constructors ----

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Config":
        """Load from YAML, then apply env overrides."""
        p = Path(path)
        if not p.exists():
            raise ConfigError(
                f"Config file not found: {p}. "
                f"Copy config.example.yaml to config.yaml and fill in values."
            )
        with p.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Config":
        ai_raw = raw.get("ai") or {}
        base_url = os.getenv("EH_BASE_URL") or ai_raw.get("base_url")
        api_key = os.getenv("EH_API_KEY") or ai_raw.get("api_key")
        model = os.getenv("EH_MODEL") or ai_raw.get("model")

        missing = [k for k, v in {"base_url": base_url, "api_key": api_key, "model": model}.items() if not v]
        if missing:
            raise ConfigError(
                f"Missing required ai.{{{', '.join(missing)}}} "
                f"in config.yaml or env (EH_BASE_URL / EH_API_KEY / EH_MODEL)."
            )

        hk = raw.get("hotkey") or {}
        lang = raw.get("language") or {}
        popup = raw.get("popup") or {}
        app = raw.get("app") or {}
        storage = raw.get("storage") or {}

        return cls(
            ai=AIConfig(base_url=base_url, api_key=api_key, model=model),
            hotkey=HotkeyConfig(translate=_normalize_hotkey(hk.get("translate", "f8"))),
            language=LanguageConfig(target=lang.get("target", "zh")),
            popup=PopupConfig(
                close_on_focus_lost=popup.get("close_on_focus_lost", True),
                pause_close_on_hover=popup.get("pause_close_on_hover", True),
            ),
            app=AppConfig(
                autostart=app.get("autostart", False),
                tray=app.get("tray", True),
            ),
            storage=StorageConfig(db_path=storage.get("db_path", "data/english-helper.db")),
        )
