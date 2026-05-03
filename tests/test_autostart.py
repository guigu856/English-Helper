"""Tests for src.autostart.

Tests the pure helper functions and round-trips IO via a unique value name
under HKCU so we don't disturb a real "EnglishHelper" entry. We always
clean up in a finally block.
"""
from __future__ import annotations

import sys
import uuid

import pytest

# Skip the entire module on non-Windows so cross-platform CI doesn't choke.
if sys.platform != "win32":
    pytest.skip("autostart is Windows-only", allow_module_level=True)

from src import autostart


def test_command_string_invokes_run_pyw_with_absolute_paths():
    cmd = autostart.command()
    # Both the interpreter path and the launcher path must be quoted because
    # they may contain spaces.
    assert cmd.startswith('"')
    assert cmd.endswith('run.pyw"')
    assert "python" in cmd.lower()


def test_run_pyw_exists_at_project_root():
    """The launcher script that autostart points to must actually exist."""
    from pathlib import Path
    from src import autostart as a

    launcher = a._project_root() / "run.pyw"
    assert launcher.exists(), f"Missing launcher script: {launcher}"


def test_enable_then_disable_roundtrip():
    """Real registry write/read/delete using a unique throwaway value name."""
    test_name = f"EnglishHelperTest_{uuid.uuid4().hex[:8]}"
    try:
        assert autostart.is_enabled(test_name) is False
        autostart.enable(test_name, cmd='"C:\\does-not-matter\\pythonw.exe" -m src.main')
        assert autostart.is_enabled(test_name) is True
    finally:
        autostart.disable(test_name)
    assert autostart.is_enabled(test_name) is False


def test_disable_when_not_set_is_noop():
    test_name = f"EnglishHelperTest_{uuid.uuid4().hex[:8]}"
    # Should not raise even though the value doesn't exist.
    autostart.disable(test_name)
    assert autostart.is_enabled(test_name) is False
