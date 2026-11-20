from analytics.history import liquidity_history


def make_quote(timestamp, price=101):
    quote = {"quote_id": timestamp, "received_at_utc": timestamp, "source_mode": "REPLAY", "snapshot_completeness": "COMPLETE", "market_phase": "LO", "price_unit": "VND_PER_SHARE", "quantity_unit": "SHARES", "is_valid_book": True, "is_stale": False}
    for side, start in (("bid", 100), ("ask", price)):
        for level in range(1, 4): quote[f"{side}_price_{level}"], quote[f"{side}_qty_{level}"] = start + (-level + 1 if side == "bid" else level - 1), 10
    return quote


def test_history_orders_by_timestamp_and_marks_coverage():
    late, early = make_quote("2026-11-07T03:01:00Z"), make_quote("2026-11-07T03:00:00Z")
    result = liquidity_history([late, early])
    assert result["coverage_sufficient"] and [point["quote_id"] for point in result["points"]] == [early["quote_id"], late["quote_id"]]
