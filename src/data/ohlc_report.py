"""Write price/volume/value and intraday liquidity comparison reports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ohlc_history import intraday_liquidity_windows, load_bars, summarize


def build_report(path: str | Path = "data/processed/ohlc_history.jsonl") -> dict:
    daily = load_bars(path, timeframe="1d")
    minute = load_bars(path, timeframe="1m")
    summaries = summarize(daily)
    comparison = sorted(summaries, key=lambda row: row["total_value"], reverse=True)
    windows = intraday_liquidity_windows(minute)
    by_symbol: dict[str, dict[str, list[dict]]] = {}
    for row in windows:
        by_symbol.setdefault(row["symbol"], {"highest_value_windows": [], "lowest_value_windows": []})
    for symbol, group in by_symbol.items():
        rows = [row for row in windows if row["symbol"] == symbol]
        by_symbol[symbol]["highest_value_windows"] = sorted(rows, key=lambda row: row["value"], reverse=True)[:10]
        by_symbol[symbol]["lowest_value_windows"] = sorted(rows, key=lambda row: row["value"])[:10]
    return {
        "source": "SSI_FASTCONNECT",
        "daily_bar_count": len(daily), "intraday_1m_bar_count": len(minute),
        "price_volume_value_by_symbol": summaries,
        "liquidity_comparison_by_total_value": comparison,
        "intraday_liquidity_windows_30m": by_symbol,
        "note": "OHLCV measures executed trading activity; it does not replace SSI three-level bid/ask history.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare SSI OHLCV price and trading liquidity.")
    parser.add_argument("--input", default="data/processed/ohlc_history.jsonl")
    parser.add_argument("--output", default="outputs/qa/ohlc_liquidity_report.json")
    args = parser.parse_args()
    report = build_report(args.input)
    destination = Path(args.output); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({"daily_bars": report["daily_bar_count"], "intraday_1m_bars": report["intraday_1m_bar_count"], "output": args.output})


if __name__ == "__main__":
    main()
