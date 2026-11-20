"""Run a bounded SSI capture for one declared HOSE session window.

This command does not invent missing history or sleep across future days. Run it
once per trading window, on three additional trading days, while keeping the
same immutable raw root. The coverage and replay reports then aggregate those
captures by date.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from data.raw_writer import RawWriter
from .config import SSISettings
from .live_check import run
from .symbol_groups import normalise_symbols


WINDOW_SECONDS = {
    "morning": 150 * 60,
    "afternoon": 105 * 60,
    "full": 255 * 60,
}
VN = timezone(timedelta(hours=7))
WINDOW_CLOCKS = {
    "morning": (time(8, 55), time(11, 30)),
    "afternoon": (time(12, 55), time(14, 45)),
    "full": (time(8, 55), time(14, 45)),
}


def remaining_window_seconds(window: str, now: datetime | None = None) -> float:
    """Return seconds until the declared VN session end.

    Starting before the opening buffer is allowed so the collector can receive
    ``market.flag``. Starting after the window end is rejected rather than
    silently collecting an unrelated period.
    """
    normalized = window.lower()
    if normalized not in WINDOW_CLOCKS:
        raise ValueError(f"unknown session window: {window}")
    current = (now or datetime.now(VN)).astimezone(VN)
    _, end_clock = WINDOW_CLOCKS[normalized]
    end = datetime.combine(current.date(), end_clock, tzinfo=VN)
    if current >= end:
        raise ValueError(f"{normalized} session has already ended at {end_clock:%H:%M} Asia/Ho_Chi_Minh")
    return (end - current).total_seconds()


def capture(
    settings: SSISettings, writer: RawWriter, *, window: str,
    listen_seconds: float | None = None, symbol_rest_preflight: bool = True,
) -> dict[str, Any]:
    normalized = window.lower()
    if normalized not in WINDOW_SECONDS:
        raise ValueError(f"unknown session window: {window}")
    duration = float(listen_seconds if listen_seconds is not None else remaining_window_seconds(normalized))
    report = run(settings, writer, duration, symbol_rest_preflight=symbol_rest_preflight)
    report["session_capture"] = {
        "window": normalized,
        "listen_seconds": duration,
        "scheduled_end_vn": WINDOW_CLOCKS[normalized][1].strftime("%H:%M"),
        "required_additional_trading_days": max(0, 5 - _observed_session_days(writer.root)),
        "note": "A session is counted only from stored LIVE provider timestamps; synthetic and replay rows are excluded.",
    }
    return report


def _observed_session_days(raw_root: str | Path) -> int:
    """Count distinct LIVE quote dates in raw WS evidence without parsing payloads deeply."""
    dates: set[str] = set()
    for path in Path(raw_root).joinpath("ws").glob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                envelope = json.loads(line)
                if envelope.get("mode") != "LIVE" or envelope.get("endpoint_or_channel") != "quote":
                    continue
                timestamp = envelope.get("provider_timestamp_raw") or envelope.get("payload", {}).get("trading_time")
                if timestamp:
                    dates.add(str(timestamp)[:10])
        except (OSError, json.JSONDecodeError):
            continue
    return len(dates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one bounded SSI HOSE session window.")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--window", choices=sorted(WINDOW_SECONDS), required=True)
    parser.add_argument("--listen-seconds", type=float, default=None, help="Override the declared window duration for a controlled test")
    parser.add_argument("--report", default=None)
    parser.add_argument("--symbols", default=None, help="Comma-separated one-run override; does not modify .env")
    parser.add_argument("--status-path", default=None, help="Separate status file for concurrent collectors")
    parser.add_argument("--skip-symbol-rest", action="store_true", help="Skip per-symbol REST checks; masterdata and WebSocket still run")
    args = parser.parse_args()
    settings = SSISettings.from_env(args.env)
    if args.symbols is not None:
        symbols = normalise_symbols(args.symbols.split(","))
        if not symbols:
            parser.error("--symbols must contain at least one valid ticker")
        settings = replace(settings, symbols=symbols, collection_scope="WATCHLIST")
    if args.status_path:
        settings = replace(settings, status_path=Path(args.status_path))
    report = capture(
        settings, RawWriter(args.raw_root), window=args.window,
        listen_seconds=args.listen_seconds,
        symbol_rest_preflight=not args.skip_symbol_rest,
    )
    destination = Path(args.report or f"outputs/qa/ssi_capture_{args.window}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"window": args.window, "acceptance": report.get("acceptance"), "session_capture": report["session_capture"]}, ensure_ascii=False))
    if report.get("acceptance", {}).get("status") != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
