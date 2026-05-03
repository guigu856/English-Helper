"""Tests for src.config."""
from __future__ import annotations

import textwrap

import pytest

from src.config import Config, ConfigError


def _write(tmp_path, body: str):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def test_load_full(tmp_path):
    p = _write(tmp_path, """
        ai:
          base_url: https://api.example.com/v1
          api_key: sk-abc
          model: gpt-test
        hotkey:
          translate: ctrl+shift+t
        language:
          target: ja
        popup:
          close_on_focus_lost: false
          pause_close_on_hover: false
        app:
          autostart: true
          tray: false
        storage:
          db_path: data/x.db
    """)
    cfg = Config.load(p)
    assert cfg.ai.base_url == "https://api.example.com/v1"
    assert cfg.ai.api_key == "sk-abc"
    assert cfg.ai.model == "gpt-test"
    assert cfg.hotkey.translate == "ctrl+shift+t"
    assert cfg.language.target == "ja"
    assert cfg.popup.close_on_focus_lost is False
    assert cfg.app.autostart is True
    assert cfg.storage.db_path == "data/x.db"


def test_hotkey_is_normalized_lowercase_no_spaces(tmp_path):
    p = _write(tmp_path, """
        ai:
          base_url: x
          api_key: y
          model: z
        hotkey:
          translate: " Ctrl + Alt + D "
    """)
    cfg = Config.load(p)
    assert cfg.hotkey.translate == "ctrl+alt+d"


def test_defaults_applied(tmp_path):
    p = _write(tmp_path, """
        ai:
          base_url: x
          api_key: y
          model: z
    """)
    cfg = Config.load(p)
    assert cfg.hotkey.translate == "f8"
    assert cfg.language.target == "zh"
    assert cfg.popup.close_on_focus_lost is True
    assert cfg.app.tray is True
    assert cfg.storage.db_path == "data/english-helper.db"


def test_env_override(tmp_path, monkeypatch):
    p = _write(tmp_path, """
        ai:
          base_url: from-yaml
          api_key: yaml-key
          model: yaml-model
    """)
    monkeypatch.setenv("EH_API_KEY", "env-key")
    monkeypatch.setenv("EH_BASE_URL", "env-url")
    cfg = Config.load(p)
    assert cfg.ai.api_key == "env-key"
    assert cfg.ai.base_url == "env-url"
    assert cfg.ai.model == "yaml-model"


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        Config.load(tmp_path / "nope.yaml")


def test_missing_required(tmp_path):
    p = _write(tmp_path, """
        ai:
          base_url: x
    """)
    with pytest.raises(ConfigError, match="api_key"):
        Config.load(p)
