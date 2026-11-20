"""Chronological liquidity series; each point uses only its own snapshot."""
from __future__ import annotations
from typing import Any
from finance.liquidity import liquidity_metrics


def liquidity_history(quotes: list[dict[str, Any]], *, minimum_eligible: int = 2) -> dict[str, Any]:
    ordered = sorted(quotes, key=lambda quote: (quote.get("received_at_utc", ""), quote.get("quote_id", "")))
    points = []
    for quote in ordered:
        metrics = liquidity_metrics(quote)
        points.append({"quote_id": quote.get("quote_id"), "received_at_utc": quote.get("received_at_utc"), "source_mode": quote.get("source_mode"), "is_eligible": metrics["is_eligible"], "spread_abs": metrics["spread_abs"], "bid_depth_3": metrics["bid_depth_3"], "ask_depth_3": metrics["ask_depth_3"], "obi_3": metrics["obi_3"]})
    eligible = sum(point["is_eligible"] for point in points)
    return {"coverage_sufficient": eligible >= minimum_eligible, "eligible_snapshot_count": eligible, "total_snapshot_count": len(points), "points": points}
