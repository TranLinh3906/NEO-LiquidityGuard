"""Validation rules for the W2/W3 quote contract."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def parse_price(value: Any) -> tuple[Decimal | None, str | None]:
    if value is None or value == "":
        return None, "MISSING"
    if isinstance(value, bool):
        return None, "NON_NUMERIC"
    try:
        price = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None, "NON_NUMERIC"
    return (price, None) if price > 0 else (None, "NON_POSITIVE")


def parse_qty(value: Any) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return None, "MISSING"
    if isinstance(value, bool):
        return None, "INVALID"
    try:
        quantity = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None, "INVALID"
    if quantity < 0 or quantity != quantity.to_integral_value():
        return None, "INVALID"
    return int(quantity), None


def validate_book(quote: dict[str, Any], *, units_verified: bool = False, allowed_phases: set[str] | None = None) -> dict[str, Any]:
    """Add quality flags without inventing missing values or mutating raw fields."""
    flags: list[str] = list(quote.get("quality_flags", []))
    if not quote.get("symbol"):
        flags.append("MISSING_SYMBOL")
    bid_prices: list[Decimal | None] = []
    ask_prices: list[Decimal | None] = []
    for side, prices in (("bid", bid_prices), ("ask", ask_prices)):
        for level in range(1, 4):
            price, price_error = parse_price(quote.get(f"{side}_price_{level}"))
            qty, qty_error = parse_qty(quote.get(f"{side}_qty_{level}"))
            quote[f"{side}_price_{level}"] = str(price) if price is not None else None
            quote[f"{side}_qty_{level}"] = qty
            prices.append(price)
            if price_error == "NON_NUMERIC": flags.append(f"NON_NUMERIC_{side.upper()}_PRICE")
            elif price_error: flags.append(f"MISSING_{side.upper()}_LEVEL")
            if qty_error: flags.append("INVALID_QTY" if qty_error == "INVALID" else f"MISSING_{side.upper()}_LEVEL")
    if all(price is not None for price in bid_prices) and bid_prices != sorted(bid_prices, reverse=True):
        flags.append("INVALID_BID_LEVEL_ORDER")
    if all(price is not None for price in ask_prices) and ask_prices != sorted(ask_prices):
        flags.append("INVALID_ASK_LEVEL_ORDER")
    if bid_prices[0] is not None and ask_prices[0] is not None and ask_prices[0] <= bid_prices[0]:
        flags.append("CROSSED_OR_LOCKED_BOOK")
    phase = quote.get("market_phase")
    if not phase: flags.append("MISSING_MARKET_PHASE")
    elif allowed_phases is not None and phase not in allowed_phases: flags.append("OUTSIDE_ALLOWED_PHASE")
    if not units_verified:
        flags.extend(["UNKNOWN_PRICE_UNIT", "UNKNOWN_QTY_UNIT"])
    if quote.get("snapshot_completeness") != "COMPLETE": flags.append("UNKNOWN_SNAPSHOT_SEMANTICS")
    quote["quality_flags"] = sorted(set(flags))
    structural_errors = {"MISSING_SYMBOL", "NON_NUMERIC_BID_PRICE", "NON_NUMERIC_ASK_PRICE", "INVALID_QTY", "INVALID_BID_LEVEL_ORDER", "INVALID_ASK_LEVEL_ORDER", "CROSSED_OR_LOCKED_BOOK", "UNEXPECTED_PROVIDER", "UNEXPECTED_SOURCE"}
    quote["is_valid_book"] = not any(flag in structural_errors for flag in quote["quality_flags"])
    quote["is_simulatable"] = quote["is_valid_book"] and quote.get("snapshot_completeness") == "COMPLETE" and units_verified and phase in (allowed_phases or set())
    return quote
