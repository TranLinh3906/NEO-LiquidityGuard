"""Streamlit Community Cloud entrypoint for LiquidityGuard."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ``app.py`` is the deployment entrypoint while ``src/app`` is the real
# package.  Expose its search path so importing ``app.universe`` from the
# repository root remains valid instead of being shadowed by this file.
__path__ = [str(SRC / "app")]
if __spec__ is not None:
    __spec__.submodule_search_locations = __path__


def main() -> None:
    """Load the packaged dashboard."""
    from app.dashboard import main as dashboard_main

    dashboard_main()


if __name__ == "__main__":
    main()
