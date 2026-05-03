"""Windows auto-start at user login via the HKCU Run registry key.

We write a value under:
    HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run

This is the standard, user-scope, no-admin-required mechanism. The Run key
does not support specifying a working directory, so the launched process
must self-correct cwd (see src/main.py top-level os.chdir).

The launched command uses `pythonw.exe` (the GUI subsystem variant of the
Python interpreter) so no console window flashes on login.

Public API:
    is_enabled() -> bool
    enable()     -> None
    disable()    -> None
    command()    -> str   # the literal string we'd register

All three IO functions accept an optional `value_name` so tests can use a
unique key without touching the real "EnglishHelper" entry.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# winreg is a Windows-only stdlib module. Importing it on other platforms
# raises ImportError; we tolerate that so unit tests on the same Windows
# machine still work, but cross-platform imports of this module fail loudly
# (which is fine — autostart only makes sense on Windows).
import winreg  # noqa: E402


REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "EnglishHelper"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _pythonw_exe() -> Path:
    """Locate pythonw.exe next to the active python.exe; fallback to python.exe."""
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def command() -> str:
    """Build the command string to register in the Run key.

    We invoke a launcher script (`run.pyw`) by absolute path rather than
    `pythonw.exe -m src.main`, because the Run key starts processes with
    cwd=C:\\Windows\\system32, where `-m src.main` cannot locate the `src`
    package (it lives only on the project's path). The launcher script
    self-corrects cwd before importing anything.

    Quotes around both paths are required: virtualenv paths commonly contain
    spaces (e.g. 'C:\\Users\\First Last\\...').
    """
    launcher = _project_root() / "run.pyw"
    return f'"{_pythonw_exe()}" "{launcher}"'


def is_enabled(value_name: str = VALUE_NAME) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.QueryValueEx(key, value_name)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable(value_name: str = VALUE_NAME, cmd: Optional[str] = None) -> None:
    cmd = cmd or command()
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, cmd)


def disable(value_name: str = VALUE_NAME) -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, value_name)
    except FileNotFoundError:
        pass
