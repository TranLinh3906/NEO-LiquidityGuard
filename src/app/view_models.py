"""Read-only data access and conservative UI eligibility over existing finance."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3

from data.normalize_quotes import normalise_envelope
from finance.eligibility import assess_continuous_book
from finance.execution import simulate_sweep
from finance.liquidity import liquidity_metrics

ROOT = Path(__file__).resolve().parents[2]
VN = timezone(timedelta(hours=7))


def parse_time(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(str(value), "%Y/%m/%d %H:%M:%S")
        except ValueError:
            return None
    return (dt.replace(tzinfo=VN) if dt.tzinfo is None else dt).astimezone(VN)


def local_time(value, short=False):
    dt = parse_time(value)
    return dt.strftime("%H:%M:%S" if short else "%d/%m/%Y %H:%M:%S") if dt else "—"


def read_status():
    try:
        return json.loads((ROOT / "data/runtime/collector_status.json").read_text())
    except (OSError, ValueError):
        return {"state": "offline"}


def synthetic_quotes(symbol):
    """Deterministic UI fixtures, generated only in explicit SYNTHETIC_TEST."""
    symbol = str(symbol or "").strip().upper()
    if not symbol or not symbol.isalnum():
        return []
    sample = json.loads((ROOT / "data_sample/synthetic_ssi_quote_envelope.jsonl").read_text().splitlines()[0])
    # Stable, symbol-specific fixture base. This makes TEST usable for every
    # captured universe symbol without ever presenting the value as SSI LIVE.
    base = {"FPT": 100000, "VPB": 20000, "SSI": 30000}.get(
        symbol, 10_000 + (sum((index + 1) * ord(char) for index, char in enumerate(symbol)) % 2_800) * 50,
    )
    rows = []
    for i in range(40):
        env = deepcopy(sample)
        dt = datetime(2026, 11, 9, 9, 15, tzinfo=VN) + timedelta(minutes=i)
        offset = (i % 9 - 4) * 50
        mid = base + offset
        env.update(raw_event_id=f"demo-{symbol}-{i:03}", symbol_hint=symbol,
                   received_at_utc=dt.astimezone(timezone.utc).isoformat(), provider_timestamp_raw=dt.isoformat())
        env["payload"].update(symbol=symbol, trading_time=dt.isoformat(),
            bid_prices=[mid - 50, mid - 100, mid - 150], ask_prices=[mid + 50, mid + 100, mid + 150],
            bid_volumes=[1000 + i * 11, 800 + (i % 7) * 45, 600 + (i % 5) * 60],
            ask_volumes=[900 + (i % 4) * 50, 1100 + i * 9, 1200 + (i % 6) * 60])
        rows.extend(normalise_envelope(env, price_unit="VND_PER_SHARE", quantity_unit="SHARES", allowed_phases={"LO"}, complete_book_verified=True, unit_evidence_ref="SYNTHETIC_FIXTURE"))
    return rows


def resolve_quote_database(mode, database=None):
    if database is not None:
        return Path(database)
    primary = ROOT / "data/processed/quotes.sqlite"
    if primary.exists() or mode != "REPLAY":
        return primary
    return ROOT / "data_sample/ssi_compact_replay.sqlite"


def load_quotes(mode, symbol, database=None):
    if mode == "SYNTHETIC_TEST":
        return synthetic_quotes(symbol)
    path = resolve_quote_database(mode, database)
    if not path.exists():
        return []
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        records = connection.execute("SELECT quote_json FROM quotes WHERE provider='SSI' AND source='SSI_FASTCONNECT' AND source_mode='LIVE' AND symbol=? ORDER BY received_at_utc, quote_id", (symbol,)).fetchall()
    rows = [json.loads(record[0]) for record in records]
    if mode == "REPLAY":
        rows = [{**row, "source_mode": "REPLAY", "original_source_mode": "LIVE"} for row in rows]
    return rows


def assess(quote, mode, status, *, stale_seconds=60, now=None):
    if not quote:
        return {"allowed": False, "label": "NO_DATA", "reasons": ["Chưa có snapshot cho mã và chế độ này."], "age_seconds": None}
    reasons = list(assess_continuous_book(quote).reasons)
    current = now or datetime.now(VN)
    when = parse_time(quote.get("quote_time_vn") or quote.get("received_at_utc"))
    age = (current - when).total_seconds() if when else None
    if mode != "SYNTHETIC_TEST":
        if not quote.get("raw_event_id"):
            reasons.append("Thiếu lineage tới raw event đã lưu")
        if quote.get("time_source") != "PROVIDER":
            reasons.append("Timestamp nguồn SSI chưa xác minh")
        if not quote.get("unit_evidence_ref"):
            reasons.append("Thiếu bằng chứng đơn vị giá/khối lượng SSI")
        if not quote.get("complete_book_verified"):
            reasons.append("Chưa xác minh quote là snapshot hoàn chỉnh")
        if quote.get("market_phase_source") != "SSI_MARKET_FLAG":
            reasons.append("Thiếu market.flag cùng sàn và thời điểm")
    if mode == "LIVE":
        if status.get("state") != "online":
            reasons.append("Collector OFFLINE")
        if age is None or age > stale_seconds or age < -5:
            reasons.append("STALE: timestamp vượt ngưỡng độ mới")
        heartbeat = parse_time(status.get("updated_at_utc"))
        if heartbeat is None or (current - heartbeat).total_seconds() > stale_seconds:
            reasons.append("Trạng thái kết nối đã cũ")
    reasons = list(dict.fromkeys(reasons))
    label = "SYNTHETIC_TEST" if mode == "SYNTHETIC_TEST" else "REPLAY_VALID" if mode == "REPLAY" else "LIVE_VALID"
    if reasons:
        label = "OFFLINE" if mode == "LIVE" and status.get("state") != "online" else "LIVE_UNVERIFIED" if mode == "LIVE" else "BLOCKED"
    return {"allowed": not reasons, "label": label, "reasons": reasons, "age_seconds": age}


def make_view(quote, mode, status, side, quantity, *, stale_seconds=60, now=None):
    trust = assess(quote, mode, status, stale_seconds=stale_seconds, now=now)
    metrics = liquidity_metrics(quote) if quote and trust["allowed"] else {}
    simulation = simulate_sweep(deepcopy(quote), side, int(quantity)) if quote and trust["allowed"] else None
    return {"quote": quote, "mode": mode, "status": status, "trust": trust,
            "metrics": metrics, "simulation": simulation, "side": side, "quantity": quantity,
            "snapshot_id": quote.get("quote_id") if quote else None}


def history_points(rows, mode, status):
    output = []
    for row in rows:
        # Historical validation deliberately ignores the collector's present uptime.
        gate = assess(row, "SYNTHETIC_TEST" if mode == "SYNTHETIC_TEST" else "REPLAY", status)
        if gate["allowed"]:
            metric = liquidity_metrics(row)
            output.append({**metric, "time": parse_time(row.get("quote_time_vn") or row.get("received_at_utc")), "snapshot_id": row["quote_id"]})
    return output


def is_observable_book(quote):
    """Allow read-only book charts without weakening the simulation gate."""
    if not quote or quote.get("provider") != "SSI" or quote.get("source") != "SSI_FASTCONNECT":
        return False
    if quote.get("snapshot_completeness") != "COMPLETE" or not quote.get("complete_book_verified"):
        return False
    if quote.get("price_unit") != "VND_PER_SHARE" or quote.get("quantity_unit") != "SHARES":
        return False
    if not quote.get("is_valid_book", False):
        return False
    try:
        active_by_side = {}
        for side in ("bid", "ask"):
            active_prices = []
            for level in range(1, 4):
                price = quote.get(f"{side}_price_{level}")
                quantity = float(quote[f"{side}_qty_{level}"])
                if quantity < 0 or not quantity.is_integer():
                    return False
                # SSI explicitly documents [0,0] as an empty level in an
                # otherwise complete latest-book snapshot. Normalisation maps
                # that zero price to None. It is observable, but never a fill.
                if price in (None, "", 0, "0"):
                    if quantity != 0:
                        return False
                    continue
                numeric_price = float(price)
                if numeric_price <= 0:
                    return False
                active_prices.append(numeric_price)
            active_by_side[side] = active_prices
            if side == "bid" and active_prices != sorted(active_prices, reverse=True):
                return False
            if side == "ask" and active_prices != sorted(active_prices):
                return False
        if not active_by_side["bid"] and not active_by_side["ask"]:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    if active_by_side["bid"] and active_by_side["ask"]:
        try:
            if float(quote["ask_price_1"]) <= float(quote["bid_price_1"]):
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


def observation_liquidity_metrics(quote):
    """Read-only metrics for a verified book, independent of market phase."""
    if not is_observable_book(quote):
        return {}
    try:
        bid_prices = [Decimal(str(quote.get(f"bid_price_{i}"))) if quote.get(f"bid_price_{i}") not in (None, "", 0, "0") else None for i in range(1, 4)]
        ask_prices = [Decimal(str(quote.get(f"ask_price_{i}"))) if quote.get(f"ask_price_{i}") not in (None, "", 0, "0") else None for i in range(1, 4)]
        bid_qty = [Decimal(str(quote[f"bid_qty_{i}"])) for i in range(1, 4)]
        ask_qty = [Decimal(str(quote[f"ask_qty_{i}"])) for i in range(1, 4)]
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return {}
    bid_depth, ask_depth = sum(bid_qty), sum(ask_qty)
    has_two_sided_top = bid_prices[0] is not None and ask_prices[0] is not None
    spread = ask_prices[0] - bid_prices[0] if has_two_sided_top else None
    mid = (ask_prices[0] + bid_prices[0]) / Decimal(2) if has_two_sided_top else None
    total_depth = bid_depth + ask_depth
    return {
        "spread_abs": spread,
        "mid_price": mid,
        "spread_pct": spread / mid * 100 if mid and mid > 0 else None,
        "spread_bps": spread / mid * 10_000 if mid and mid > 0 else None,
        "bid_depth_3": bid_depth,
        "ask_depth_3": ask_depth,
        "bid_notional_3": sum((price or Decimal(0)) * qty for price, qty in zip(bid_prices, bid_qty)),
        "ask_notional_3": sum((price or Decimal(0)) * qty for price, qty in zip(ask_prices, ask_qty)),
        "obi_3": (bid_depth - ask_depth) / total_depth if total_depth else None,
        "is_observation_only": True,
    }


def observation_history_points(rows):
    """Metrics for labelled observation charts; never used for simulation."""
    output = []
    for row in rows:
        if is_observable_book(row):
            metric = observation_liquidity_metrics(row)
            output.append({
                **metric,
                "time": parse_time(row.get("quote_time_vn") or row.get("received_at_utc")),
                "snapshot_id": row["quote_id"],
                "market_phase": row.get("market_phase"),
                "market_phase_source": row.get("market_phase_source"),
            })
    return output


def coverage_points(quote, side, maximum):
    sizes = sorted({1, *[max(1, int(maximum * part / 20)) for part in range(1, 31)]})
    return [{"quantity": size, "coverage": float(simulate_sweep(quote, side, size)["coverage_ratio"] * 100),
             "impact": simulate_sweep(quote, side, size)["slippage_bps"]} for size in sizes]
