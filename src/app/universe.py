"""SSI security universe and exchange/sector metadata for the dashboard."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from ssi_api.symbol_groups import VN30_AS_OF, VN30_SYMBOLS


BOARD_LABELS = {
    "HOSE": "HOSE — Sở GDCK TP.HCM",
    "HNX": "HNX — Sở GDCK Hà Nội",
    "UPCOM": "UPCoM",
}
EQUITY_BOARDS = frozenset(BOARD_LABELS)


def _sector_overrides(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["symbol"].strip().upper(): row["sector"].strip() for row in csv.DictReader(handle) if row.get("symbol") and row.get("sector")}


def load_universe(
    raw_root: str | Path = "data/raw/rest",
    overrides_path: str | Path = "data/universe/sector_overrides.csv",
) -> list[dict[str, Any]]:
    """Load every symbol from the latest non-empty SSI masterdata capture.

    SSI masterdata currently exposes symbol/board/reference fields, not a
    sector taxonomy.  Sector labels therefore come only from an explicit,
    reviewable override file; missing labels stay ``UNCLASSIFIED`` instead of
    being guessed from ticker names.
    """
    root = Path(raw_root)
    latest: list[dict[str, Any]] = []
    latest_at = ""
    info_by_symbol: dict[str,dict[str,Any]] = {}
    info_at: dict[str,str] = {}
    for path in sorted(root.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                # History responses can be large; skip unrelated envelopes.
                if 'masterdata' not in line.lower() and 'securitiesbyboard' not in line.lower():
                    continue
                try: event = json.loads(line)
                except json.JSONDecodeError: continue
                if str(event.get("endpoint_or_channel","")).lower().endswith("securitiesbyboard"):
                    payload=event.get("payload",{})
                    items=payload.get("data",[]) if isinstance(payload,dict) else payload
                    received=str(event.get("received_at_utc") or "")
                    if isinstance(items,list):
                        for item in items:
                            symbol=str(item.get("symbol") or "").strip().upper()
                            if symbol and received>=info_at.get(symbol,""):
                                info_by_symbol[symbol]=item;info_at[symbol]=received
                    continue
                if not str(event.get("endpoint_or_channel", "")).lower().endswith("masterdata"):
                    continue
                payload = event.get("payload")
                received = str(event.get("received_at_utc") or "")
                if isinstance(payload, list) and payload and received >= latest_at:
                    latest, latest_at = payload, received
    overrides = _sector_overrides(Path(overrides_path))
    master={str(item.get("symbol") or "").upper():item for item in latest}
    for symbol,info in info_by_symbol.items():
        if symbol not in master and info.get("board") in EQUITY_BOARDS:
            master[symbol]={"symbol":symbol,"board":info["board"],"trading_date":None,"ref_price":None}
    universe: list[dict[str, Any]] = []
    for item in master.values():
        symbol = str(item.get("symbol") or "").strip().upper()
        board = str(item.get("board") or "UNKNOWN").strip().upper()
        if not symbol or board not in EQUITY_BOARDS:
            continue
        info=info_by_symbol.get(symbol,{})
        icb=info.get("icb_name") or info.get("icbName")
        sector = overrides.get(symbol, icb or "UNCLASSIFIED")
        universe.append({
            "symbol": symbol,
            "board": board,
            "board_label": BOARD_LABELS.get(board, board),
            "sector": sector,
            "sector_source": "REVIEWED_OVERRIDE" if symbol in overrides else "SSI_ICB" if icb else "NOT_IN_SSI_MASTERDATA",
            "company_name":info.get("symbol_name_vi") or info.get("symbolNameVi"),
            "stock_type":info.get("stock_type") or info.get("stockType") or "UNKNOWN",
            "icb_code":info.get("icb_code") or info.get("icbCode"),
            "icb_sector":icb,
            "index_group": "VN30" if symbol in VN30_SYMBOLS else None,
            "index_as_of": VN30_AS_OF if symbol in VN30_SYMBOLS else None,
            "trading_date": item.get("trading_date"),
            "ref_price": item.get("ref_price"),
        })
    return sorted(universe, key=lambda row: row["symbol"])


def restrict_to_latest_capture(
    rows: list[dict[str, Any]],
    reports_root: str | Path = "outputs/qa",
) -> list[dict[str, Any]]:
    """Keep only symbols from the newest persisted SSI capture run.

    The dashboard must not imply that the complete SSI master catalogue was
    collected live.  A capture report is the auditable source of the actual
    subscription scope (230 symbols on 2026-11-19 in the current dataset).
    """
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for path in Path(reports_root).glob("ssi_capture_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        symbols = payload.get("symbols")
        checked_at = str(payload.get("checked_at_utc") or "")
        if payload.get("provider") != "SSI" or not checked_at or not isinstance(symbols, list) or not symbols:
            continue
        candidates.append((checked_at, path, payload))
    if not candidates:
        return []
    checked_at, source_path, capture = max(candidates, key=lambda item: item[0])
    ordered = list(dict.fromkeys(str(symbol).strip().upper() for symbol in capture["symbols"] if str(symbol).strip()))
    by_symbol = {row["symbol"]: row for row in rows}
    capture_date = checked_at[:10]
    # Streamlit Cloud intentionally does not receive the multi-gigabyte RAW
    # masterdata directory.  The committed capture report remains the source
    # of scope, while the committed coverage report can restore only the
    # observed exchange label.  Missing company/sector metadata stays explicit
    # and is never invented.
    board_by_symbol: dict[str, str] = {}
    coverage_path = Path(reports_root) / "coverage_report.csv"
    if coverage_path.is_file():
        try:
            with coverage_path.open(newline="", encoding="utf-8-sig") as handle:
                for row in csv.DictReader(handle):
                    day = str(row.get("trade_date") or "").replace("/", "-")
                    board = str(row.get("board") or "").upper()
                    symbol = str(row.get("symbol") or "").upper()
                    if day == capture_date and symbol and board in EQUITY_BOARDS:
                        board_by_symbol[symbol] = board
        except (OSError, csv.Error):
            board_by_symbol = {}

    def captured_row(symbol: str) -> dict[str, Any]:
        if symbol in by_symbol:
            return by_symbol[symbol]
        board = board_by_symbol.get(symbol, "UNKNOWN")
        return {
            "symbol": symbol,
            "board": board,
            "board_label": BOARD_LABELS.get(board, board),
            "sector": "UNCLASSIFIED",
            "sector_source": "CAPTURE_REPORT_ONLY",
            "company_name": None,
            "stock_type": "Stock",
            "icb_code": None,
            "icb_sector": None,
            "index_group": "VN30" if symbol in VN30_SYMBOLS else None,
            "index_as_of": VN30_AS_OF if symbol in VN30_SYMBOLS else None,
            "trading_date": capture_date.replace("-", "/"),
            "ref_price": None,
        }

    return [
        {
            **captured_row(symbol),
            "capture_date": capture_date,
            "capture_checked_at_utc": checked_at,
            "capture_report": source_path.name,
            "capture_scope_size": len(ordered),
        }
        for symbol in ordered
    ]


def universe_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "symbols": len(rows),
        "hose": sum(row["board"] == "HOSE" for row in rows),
        "hnx": sum(row["board"] == "HNX" for row in rows),
        "upcom": sum(row["board"] == "UPCOM" for row in rows),
        "unclassified_sector": sum(row["sector"] == "UNCLASSIFIED" for row in rows),
        "vn30": sum(row.get("index_group") == "VN30" for row in rows),
    }
