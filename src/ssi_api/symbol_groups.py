"""Named SSI symbol groups and safe, data-driven collection-scope resolution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


# HOSE constituent announcement for the July 2026 review.  Keep the as-of
# date and source beside the values so a future rebalance cannot be mistaken
# for an automatically updating list.
VN30_AS_OF = "2026-07"
VN30_SOURCE = (
    "https://staticfile.hsx.vn/Uploads/UploadDocuments/2479382/"
    "15072026%20CBTT%20-%20Danh%20muc%20thanh%20phan%20HOSE-Index%20thang%207.2026.pdf"
)
VN30_SYMBOLS = (
    "ACB", "BID", "BSR", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", "LPB",
    "MBB", "MCH", "MSN", "MWG", "SAB", "SHB", "SSB", "SSI", "STB", "TCB",
    "TCX", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VPL", "VRE",
)


def normalise_symbols(values: Iterable[str]) -> tuple[str, ...]:
    """Upper-case, validate and de-duplicate tickers while preserving order."""
    output: list[str] = []
    for value in values:
        symbol = str(value).strip().upper()
        if symbol and symbol.replace("-", "").isalnum() and symbol not in output:
            output.append(symbol)
    return tuple(output)


def catalog_equities(raw_root: str | Path = "data/raw/rest") -> tuple[str, ...]:
    """Read all SSI-classified stocks from the latest saved board metadata.

    The function is deliberately local-only: choosing ``ALL`` never triggers a
    hidden network call and never invents symbols when the SSI catalogue is
    unavailable.
    """
    latest: dict[str, tuple[str, str]] = {}
    for path in sorted(Path(raw_root).glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if "securitiesbyboard" not in line.lower():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not str(event.get("endpoint_or_channel", "")).lower().endswith("securitiesbyboard"):
                    continue
                received = str(event.get("received_at_utc") or "")
                payload = event.get("payload", {})
                rows = payload.get("data", []) if isinstance(payload, dict) else payload
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    symbol = str(row.get("symbol") or "").strip().upper()
                    stock_type = str(row.get("stock_type") or row.get("stockType") or "")
                    board = str(row.get("board") or "").upper()
                    if symbol and stock_type == "Stock" and board in {"HOSE", "HNX", "UPCOM"}:
                        previous = latest.get(symbol)
                        if previous is None or received >= previous[0]:
                            latest[symbol] = (received, board)
    return tuple(sorted(latest))


def resolve_symbols(
    scope: str,
    configured: Iterable[str] = (),
    *,
    raw_root: str | Path = "data/raw/rest",
) -> tuple[str, ...]:
    """Resolve WATCHLIST, VN30 or ALL without silently falling back to 2 tickers."""
    scope = scope.strip().upper()
    supplied = normalise_symbols(configured)
    if scope == "ALL":
        symbols = catalog_equities(raw_root)
        if not symbols:
            raise ValueError("SSI_COLLECTION_SCOPE=ALL requires saved securitiesByBoard stock metadata")
        return symbols
    # An explicit list is always an intentional operator override.  The
    # built-in group is used only when SSI_SYMBOLS is blank.
    if supplied:
        return supplied
    if scope == "VN30":
        return VN30_SYMBOLS
    if scope == "WATCHLIST":
        return supplied or VN30_SYMBOLS
    raise ValueError("SSI_COLLECTION_SCOPE must be WATCHLIST, VN30, or ALL")
