"""Three-level spread, depth, and order-book imbalance calculations."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any
from .eligibility import assess_continuous_book


def _decimal(value: Any) -> Decimal | None:
    try: return Decimal(str(value))
    except (InvalidOperation, ValueError): return None


def liquidity_metrics(quote: dict[str, Any]) -> dict[str, Any]:
    eligibility = assess_continuous_book(quote)
    result: dict[str, Any] = {"is_eligible": eligibility.allowed, "rejection_reasons": list(eligibility.reasons), "spread_abs": None, "mid_price": None, "spread_pct": None, "spread_bps": None, "bid_depth_3": None, "ask_depth_3": None, "bid_notional_3": None, "ask_notional_3": None, "obi_3": None}
    if not eligibility.allowed: return result
    bid_prices, ask_prices = [_decimal(quote[f"bid_price_{i}"]) for i in range(1, 4)], [_decimal(quote[f"ask_price_{i}"]) for i in range(1, 4)]
    bid_qty, ask_qty = [_decimal(quote[f"bid_qty_{i}"]) for i in range(1, 4)], [_decimal(quote[f"ask_qty_{i}"]) for i in range(1, 4)]
    bid_depth, ask_depth = sum(bid_qty), sum(ask_qty)
    spread, mid = ask_prices[0] - bid_prices[0], (ask_prices[0] + bid_prices[0]) / Decimal(2)
    result.update({"spread_abs": spread, "mid_price": mid, "spread_pct": spread / mid * 100 if mid > 0 else None, "spread_bps": spread / mid * 10_000 if mid > 0 else None, "bid_depth_3": bid_depth, "ask_depth_3": ask_depth, "obi_3": (bid_depth - ask_depth) / (bid_depth + ask_depth) if bid_depth + ask_depth else None})
    # Notional is published only when both units were explicitly verified by eligibility.
    result["bid_notional_3"] = sum(price * qty for price, qty in zip(bid_prices, bid_qty))
    result["ask_notional_3"] = sum(price * qty for price, qty in zip(ask_prices, ask_qty))
    return result
