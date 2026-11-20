"""Streamlit Community Cloud entrypoint for LiquidityGuard."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> None:
    """Load the packaged dashboard without letting this file shadow it."""
    current = sys.modules.get(__name__)
    if sys.modules.get("app") is current and not hasattr(current, "__path__"):
        del sys.modules["app"]
    from app.dashboard import main as dashboard_main

    dashboard_main()


if __name__ == "__main__":
    main()
