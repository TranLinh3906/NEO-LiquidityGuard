"""Conservative three-level sweep simulation; this never submits an order."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any
from .eligibility import assess_continuous_book


def simulate_sweep(quote: dict[str, Any], side: str, requested_qty: int) -> dict[str, Any]:
    side = side.upper()
    if side not in {"BUY", "SELL"}: raise ValueError("side must be BUY or SELL")
    if not isinstance(requested_qty, int) or isinstance(requested_qty, bool) or requested_qty <= 0: raise ValueError("requested_qty must be a positive integer")
    eligibility = assess_continuous_book(quote)
    base = {"side": side, "requested_qty": requested_qty, "filled_qty": 0, "unfilled_qty": requested_qty, "coverage_ratio": Decimal(0), "vwap_filled": None, "best_price": None, "slippage_abs": None, "slippage_bps": None, "level_fills": [], "is_simulatable": eligibility.allowed, "rejection_reason": "; ".join(eligibility.reasons) or None, "warnings": [], "source_mode": quote.get("source_mode"), "quote_id": quote.get("quote_id")}
    if not eligibility.allowed: return base
    book_side = "ask" if side == "BUY" else "bid"
    remaining, notional = requested_qty, Decimal(0)
    for level in range(1, 4):
        price, available = Decimal(str(quote[f"{book_side}_price_{level}"])), int(quote[f"{book_side}_qty_{level}"])
        taken = min(remaining, available)
        base["level_fills"].append({"level": level, "price": price, "available_qty": available, "filled_qty": taken})
        notional += price * taken; remaining -= taken
        if remaining == 0: break
    filled = requested_qty - remaining
    base.update({"filled_qty": filled, "unfilled_qty": remaining, "coverage_ratio": Decimal(filled) / requested_qty, "total_notional": notional})
    if filled:
        best, vwap = Decimal(str(quote[f"{book_side}_price_1"])), notional / filled
        slippage = vwap - best if side == "BUY" else best - vwap
        base.update({"vwap_filled": vwap, "best_price": best, "slippage_abs": slippage, "slippage_bps": slippage / best * 10_000 if best else None})
        if slippage < 0: base["warnings"].append("negative slippage: check level ordering")
    if remaining: base["warnings"].append("quantity exceeds the observed three-level depth")
    return base
