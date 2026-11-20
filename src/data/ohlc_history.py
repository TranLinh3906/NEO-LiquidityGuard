"""Canonical SSI OHLCV history and liquidity-window analytics."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def normalize_bar(value: dict[str, Any], *, symbol: str, timeframe: str, provider: str = "SSI") -> dict[str, Any]:
    """Normalize SDK and REST field names without changing provider values."""
    row = {
        "provider": provider, "source": "SSI_FASTCONNECT", "source_mode": "HISTORICAL",
        "symbol": str(value.get("symbol") or symbol).upper(),
        "timeframe": timeframe,
        "trading_date": value.get("trading_date", value.get("tradingDate")),
        "open": value.get("open", value.get("open_price")),
        "high": value.get("high", value.get("high_price")),
        "low": value.get("low", value.get("low_price")),
        "close": value.get("close", value.get("close_price")),
        "volume": value.get("volume"),
        "value": value.get("value"),
    }
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    row["bar_id"] = hashlib.sha256(encoded).hexdigest()
    return row


def append_bars(path: str | Path, bars: Iterable[dict[str, Any]]) -> int:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if destination.exists():
        for line in destination.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(json.loads(line).get("bar_id"))
            except json.JSONDecodeError:
                continue
    inserted = 0
    with destination.open("a", encoding="utf-8") as handle:
        for bar in bars:
            if bar.get("bar_id") in existing:
                continue
            handle.write(json.dumps(bar, ensure_ascii=False, separators=(",", ":")) + "\n")
            existing.add(bar.get("bar_id")); inserted += 1
    return inserted


def load_bars(path: str | Path, *, symbol: str | None = None, timeframe: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source = Path(path)
    if not source.exists():
        return rows
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if symbol and row.get("symbol") != symbol.upper():
            continue
        if timeframe and row.get("timeframe") != timeframe:
            continue
        rows.append(row)
    return rows


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def summarize(bars: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for bar in bars:
        groups[(bar.get("symbol", "UNKNOWN"), bar.get("timeframe", "UNKNOWN"))].append(bar)
    result = []
    for (symbol, timeframe), rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda row: str(row.get("trading_date") or ""))
        first, last = ordered[0], ordered[-1]
        open_price, close_price = _number(first.get("open")), _number(last.get("close"))
        change = close_price - open_price if open_price else None
        result.append({
            "symbol": symbol, "timeframe": timeframe, "bar_count": len(rows),
            "first_date": first.get("trading_date"), "last_date": last.get("trading_date"),
            "open": first.get("open"), "high": max((_number(row.get("high")) for row in rows), default=0),
            "low": min((_number(row.get("low")) for row in rows), default=0), "close": last.get("close"),
            "price_change": change,
            "price_change_pct": (change / open_price * 100) if change is not None and open_price else None,
            "total_volume": sum(_number(row.get("volume")) for row in rows),
            "total_value": sum(_number(row.get("value")) for row in rows),
            "average_bar_volume": sum(_number(row.get("volume")) for row in rows) / len(rows),
            "average_bar_value": sum(_number(row.get("value")) for row in rows) / len(rows),
        })
    return result


def intraday_liquidity_windows(bars: Iterable[dict[str, Any]], *, bucket_minutes: int = 30) -> list[dict[str, Any]]:
    """Aggregate 1m bars by clock bucket to identify high/low liquidity periods."""
    buckets: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"volume": 0.0, "value": 0.0, "bars": 0})
    for row in bars:
        stamp = str(row.get("trading_date") or "")
        parsed = None
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                parsed = datetime.strptime(stamp, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            continue
        minute = (parsed.minute // bucket_minutes) * bucket_minutes
        key = (row.get("symbol", "UNKNOWN"), f"{parsed.hour:02d}:{minute:02d}")
        buckets[key]["volume"] += _number(row.get("volume")); buckets[key]["value"] += _number(row.get("value")); buckets[key]["bars"] += 1
    output = [{"symbol": symbol, "time_bucket": bucket, **metrics} for (symbol, bucket), metrics in buckets.items()]
    return sorted(output, key=lambda row: (row["symbol"], -row["value"], row["time_bucket"]))
