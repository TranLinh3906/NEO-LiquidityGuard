"""Observed SSI quote-session coverage without inventing unavailable history."""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta, time
import json
from pathlib import Path

from .quote_store import QuoteStore


DEFAULT_SESSION_WINDOWS = {
    "HOSE": (("09:00", "11:30"), ("13:00", "14:45")),
    "HNX": (("09:00", "11:30"), ("13:00", "14:45")),
    "UPCOM": (("09:00", "11:30"), ("13:00", "14:45")),
}


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=7)))
        except ValueError:
            return None


def _clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return time(hour, minute)


def session_metrics(times: list[datetime], *, board: str = "UNKNOWN", session_windows=None) -> dict:
    """Measure observed coverage against declared session windows.

    This reports missing opening/closing edges and in-session downtime. It never
    upgrades a short capture to a full-session claim.
    """
    windows = session_windows or DEFAULT_SESSION_WINDOWS.get(board.upper(), DEFAULT_SESSION_WINDOWS["HOSE"])
    valid = sorted(t for t in times if t is not None)
    if not valid:
        return {"session_expected_seconds": 0, "session_observed_span_seconds": 0,
                "session_coverage_ratio": 0.0, "missing_session_seconds": 0,
                "downtime_gap_count": 0, "max_downtime_seconds": 0,
                "session_windows_observed": 0, "session_windows_expected": len(windows),
                "session_status": "NO_DATA"}
    local_date = valid[0].date()
    expected = 0
    observed = 0
    downtime: list[float] = []
    windows_observed = 0
    for start_raw, end_raw in windows:
        start = datetime.combine(local_date, _clock(start_raw), tzinfo=valid[0].tzinfo)
        end = datetime.combine(local_date, _clock(end_raw), tzinfo=valid[0].tzinfo)
        expected += int((end - start).total_seconds())
        inside = [t for t in valid if start <= t <= end]
        if not inside:
            continue
        windows_observed += 1
        observed += max(0, int((inside[-1] - inside[0]).total_seconds()))
        downtime.extend((current - previous).total_seconds() for previous, current in zip(inside, inside[1:]) if (current - previous).total_seconds() > 60)
        # Missing opening/closing edges are downtime too; otherwise a short
        # midday capture would misleadingly report zero downtime.
        if (inside[0] - start).total_seconds() > 60:
            downtime.append((inside[0] - start).total_seconds())
        if (end - inside[-1]).total_seconds() > 60:
            downtime.append((end - inside[-1]).total_seconds())
    ratio = observed / expected if expected else 0.0
    return {
        "session_expected_seconds": expected,
        "session_observed_span_seconds": observed,
        "session_coverage_ratio": round(ratio, 6),
        "missing_session_seconds": max(0, expected - observed),
        "downtime_gap_count": len(downtime),
        "max_downtime_seconds": max(downtime, default=0),
        "session_windows_observed": windows_observed,
        "session_windows_expected": len(windows),
        "session_status": "FULL_SESSION" if windows_observed == len(windows) and ratio >= 0.99 else "OBSERVED_ONLY",
    }


def _masterdata_board_map(raw_root: str | Path = "data/raw/rest") -> dict[str, str]:
    """Load the newest non-empty SSI masterdata response for board attribution."""
    candidates = sorted(Path(raw_root).glob("*.jsonl"), reverse=True)
    for path in candidates:
        try:
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError):
            continue
        for envelope in reversed(rows):
            if str(envelope.get("endpoint_or_channel", "")).endswith("masterdata") and isinstance(envelope.get("payload"), list) and envelope["payload"]:
                return {str(row.get("symbol", "")).upper(): str(row.get("board", "")).upper() for row in envelope["payload"] if isinstance(row, dict) and row.get("symbol") and row.get("board")}
    return {}


def write_coverage_report(store: QuoteStore, output: str | Path, *, board_map: dict[str, str] | None = None, session_windows=None) -> list[dict]:
    """Write one observed-coverage row per SSI trade-date and symbol.

    This deliberately reports first/last/span/gaps instead of claiming full-session
    coverage. OHLC rows never enter the canonical quote store and therefore cannot
    inflate order-book coverage.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in store.records():
        observed = row.get("quote_time_vn") or row.get("received_at_utc")
        trade_date = str(observed or "UNKNOWN")[:10]
        symbol = row.get("symbol") or "UNKNOWN"
        groups.setdefault((trade_date, symbol), []).append(row)

    records: list[dict] = []
    for (trade_date, symbol), rows in sorted(groups.items()):
        times = sorted(filter(None, (_parse_time(row.get("quote_time_vn") or row.get("received_at_utc")) for row in rows)))
        gaps = [(current - previous).total_seconds() for previous, current in zip(times, times[1:])]
        phases = sorted({row.get("market_phase") for row in rows if row.get("market_phase")})
        original_modes = sorted({row.get("source_mode") for row in rows if row.get("source_mode")})
        complete = sum(row.get("snapshot_completeness") == "COMPLETE" for row in rows)
        board = (board_map or {}).get(str(symbol).upper(), "UNKNOWN")
        session = session_metrics(times, board=board, session_windows=session_windows)
        records.append({
            "provider": "SSI", "source": "SSI_FASTCONNECT",
            "trade_date": trade_date, "symbol": symbol,
            "source_modes": "|".join(original_modes), "quote_count": len(rows),
            "raw_event_count": len({row.get("raw_event_id") for row in rows if row.get("raw_event_id")}),
            "complete_snapshot_count": complete,
            "valid_snapshot_count": sum(bool(row.get("is_valid_book")) for row in rows),
            "partial_update_count": sum(row.get("update_type") == "PARTIAL_BOOK" for row in rows),
            "first_quote_time": times[0].isoformat() if times else "",
            "last_quote_time": times[-1].isoformat() if times else "",
            "observed_span_seconds": (times[-1] - times[0]).total_seconds() if len(times) >= 2 else 0,
            "gap_count_over_60s": sum(gap > 60 for gap in gaps),
            "max_gap_seconds": max(gaps, default=""),
            "market_phases": "|".join(phases),
            "board": board,
            **session,
            "coverage_status": session["session_status"],
            "notes": "Session windows are declared expectations; observed quotes do not prove continuous feed coverage. OHLC does not count as L3 quote coverage.",
        })

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "provider", "source", "trade_date", "symbol", "source_modes",
        "quote_count", "raw_event_count", "complete_snapshot_count",
        "valid_snapshot_count", "partial_update_count", "first_quote_time",
        "last_quote_time", "observed_span_seconds", "gap_count_over_60s",
        "max_gap_seconds", "market_phases", "board", "session_expected_seconds",
        "session_observed_span_seconds", "session_coverage_ratio", "missing_session_seconds",
        "downtime_gap_count", "max_downtime_seconds", "session_windows_observed",
        "session_windows_expected", "session_status", "coverage_status", "notes",
    ]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    return records


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Report observed SSI L3 quote coverage; OHLC is excluded.")
    parser.add_argument("--database", default="data/processed/quotes.sqlite")
    parser.add_argument("--output", default="outputs/qa/coverage_report.csv")
    parser.add_argument("--raw-root", default="data/raw/rest")
    args = parser.parse_args()
    store = QuoteStore(args.database)
    try:
        records = write_coverage_report(store, args.output, board_map=_masterdata_board_map(args.raw_root))
        print({"coverage_rows": len(records), "output": args.output})
    finally:
        store.close()


if __name__ == "__main__":
    main()
