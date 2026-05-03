"""Windows GUI launcher.

Used by the auto-start registry entry so that:
1) `pythonw.exe` (no console flash) is invoked,
2) cwd is set to the project root before any imports — the Run-key launches
   processes in C:\\Windows\\system32 by default, which would prevent Python
   from locating the `src` package via `-m src.main`.

Calling `pythonw run.pyw` works regardless of the caller's cwd, because we
resolve the project root from this file's path.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
# Make `src` importable when launched as a script (cwd is on sys.path[0]
# already after chdir, but keep this explicit for robustness).
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import main  # noqa: E402

raise SystemExit(main())
