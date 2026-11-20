"""Fetch SSI historical OHLCV for a watchlist and persist raw + canonical bars."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from data.ohlc_history import append_bars, normalize_bar
from data.raw_writer import RawWriter
from .client import SSIReadOnlyClient, jsonable
from .config import SSISettings


def _date_years_ago(years: int) -> str:
    today = date.today()
    try:
        return today.replace(year=today.year - years).strftime("%Y/%m/%d")
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years).strftime("%Y/%m/%d")


def run(settings: SSISettings, *, symbols: list[str], timeframe: str, from_date: str, to_date: str,
        raw_root: str | Path = "data/raw", output: str | Path = "data/processed/ohlc_history.jsonl",
        page_size: int = 1000) -> dict[str, Any]:
    missing = settings.missing_credentials()
    if missing:
        return {"status": "CONFIG_REQUIRED", "missing": list(missing), "symbols": symbols}
    client = SSIReadOnlyClient(settings); writer = RawWriter(raw_root)
    bars: list[dict[str, Any]] = []; results = {}; inserted_total = 0
    try:
        client.connect()
        for symbol in symbols:
            try:
                payload = jsonable(client.ohlc(symbol, timeframe, from_date, to_date, size=page_size, ascending=True))
                if isinstance(payload, dict) and "data" in payload:
                    payload_rows = payload["data"]
                else:
                    payload_rows = payload
                payload_rows = payload_rows if isinstance(payload_rows, list) else []
                writer.write(provider="SSI", source="SSI_FASTCONNECT", mode="LIVE", transport="REST",
                             endpoint_or_channel="/api/v3/data/ohlc", payload={"symbol": symbol, "timeframe": timeframe,
                             "from": from_date, "to": to_date, "data": payload_rows}, symbol_hint=symbol, http_status=200)
                normalized = [normalize_bar(row, symbol=symbol, timeframe=timeframe) for row in payload_rows if isinstance(row, dict)]
                bars.extend(normalized)
                inserted = append_bars(output, normalized)
                inserted_total += inserted
                results[symbol] = {"status": "PASS", "bar_count": len(normalized), "bars_inserted": inserted}
            except Exception as exc:
                results[symbol] = {"status": "FAIL", "error_type": type(exc).__name__}
    finally:
        client.close()
    return {"status": "PASS", "timeframe": timeframe, "from": from_date, "to": to_date,
            "symbols": symbols, "results": results, "bars_fetched": len(bars), "bars_inserted": inserted_total,
            "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SSI OHLCV history; this is not L3 order-book history.")
    parser.add_argument("--env", default=".env"); parser.add_argument("--symbols", default=None)
    parser.add_argument("--timeframe", choices=("1m", "3m", "5m", "15m", "30m", "1h", "1d"), default="1d")
    parser.add_argument("--from-date", default=None); parser.add_argument("--to-date", default=None)
    parser.add_argument("--years", type=int, default=5); parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--output", default="data/processed/ohlc_history.jsonl"); parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args(); settings = SSISettings.from_env(args.env)
    symbols = [item.strip().upper() for item in (args.symbols.split(",") if args.symbols else settings.symbols) if item.strip()]
    years = min(args.years, 1) if args.timeframe != "1d" else args.years
    report = run(settings, symbols=symbols, timeframe=args.timeframe,
                 from_date=args.from_date or _date_years_ago(years),
                 to_date=args.to_date or date.today().strftime("%Y/%m/%d"), raw_root=args.raw_root,
                 output=args.output, page_size=args.page_size)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("status") != "PASS": raise SystemExit(2)


if __name__ == "__main__":
    main()
