from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root and common venv layouts are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_PARENT = PROJECT_ROOT.parent
SITE_PACKAGES = [
    PROJECT_ROOT / "venv" / "Lib" / "site-packages",  # Windows layout
    PROJECT_ROOT / "venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
    PROJECT_ROOT / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
]

# Parent first so package resolution prefers the outer package (with verification.py)
if str(PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(PROJECT_PARENT))

for runtime_path in (PROJECT_ROOT, *SITE_PACKAGES):
    if runtime_path.exists():
        str_path = str(runtime_path)
        if str_path not in sys.path:
            sys.path.append(str_path)


def test_imports():
    # Prime sys.modules to avoid resolution issues inside package __init__
    import metamath2py.verification  # noqa: F401
    # These imports should resolve when sys.path is set correctly
    import metamath2py.classes.VLEL  # noqa: F401
    import metamath2py.classes.SW6P  # noqa: F401
    import metamath2py.classes.A0K0  # noqa: F401
