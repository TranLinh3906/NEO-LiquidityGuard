"""Decide whether a quote is safe to analyse or simulate."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True, slots=True)
class Eligibility:
    allowed: bool
    reasons: tuple[str, ...]


def _positive(value: Any) -> bool:
    try: return Decimal(str(value)) > 0
    except (InvalidOperation, ValueError): return False


def _valid_qty(value: Any) -> bool:
    try:
        number = Decimal(str(value))
        return number >= 0 and number == number.to_integral_value()
    except (InvalidOperation, ValueError): return False


def assess_continuous_book(quote: dict[str, Any], allowed_phases: set[str] | None = None) -> Eligibility:
    phases, reasons = allowed_phases or {"LO"}, []
    # W4 is SSI-only: do not silently run financial metrics on an unlabelled
    # or differently sourced record.  Missing legacy fields remain tolerated
    # for backwards-compatible unit fixtures; present values must be correct.
    if "provider" in quote and quote.get("provider") != "SSI": reasons.append("provider is not SSI")
    if "source" in quote and quote.get("source") != "SSI_FASTCONNECT": reasons.append("source is not SSI_FASTCONNECT")
    if quote.get("snapshot_completeness") != "COMPLETE": reasons.append("snapshot is incomplete or WS semantics are unverified")
    if quote.get("is_stale"): reasons.append("quote is stale")
    if quote.get("market_phase") not in phases: reasons.append("market phase is not allowed")
    if not quote.get("price_unit") or quote.get("price_unit") == "UNVERIFIED" or not quote.get("quantity_unit") or quote.get("quantity_unit") == "UNVERIFIED": reasons.append("price or quantity unit is unverified")
    if not quote.get("is_valid_book", True): reasons.append("quote failed structural validation")
    for side in ("bid", "ask"):
        prices = []
        for level in range(1, 4):
            price, qty = quote.get(f"{side}_price_{level}"), quote.get(f"{side}_qty_{level}")
            prices.append(price)
            if not _positive(price): reasons.append(f"{side}{level} price is not positive numeric")
            if not _valid_qty(qty): reasons.append(f"{side}{level} quantity is invalid")
        if side == "bid" and all(_positive(price) for price in prices) and not (Decimal(str(prices[0])) >= Decimal(str(prices[1])) >= Decimal(str(prices[2]))): reasons.append("bid levels are not descending")
        if side == "ask" and all(_positive(price) for price in prices) and not (Decimal(str(prices[0])) <= Decimal(str(prices[1])) <= Decimal(str(prices[2]))): reasons.append("ask levels are not ascending")
    if _positive(quote.get("bid_price_1")) and _positive(quote.get("ask_price_1")) and Decimal(str(quote["ask_price_1"])) <= Decimal(str(quote["bid_price_1"])): reasons.append("book is crossed or locked")
    return Eligibility(not reasons, tuple(dict.fromkeys(reasons)))


def is_valid_continuous_book(quote: dict[str, Any]) -> bool:
    return assess_continuous_book(quote).allowed
