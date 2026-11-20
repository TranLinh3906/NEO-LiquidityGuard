from decimal import Decimal
import pytest
from finance.eligibility import assess_continuous_book
from finance.execution import simulate_sweep
from finance.liquidity import liquidity_metrics


def quote():
    record = {"quote_id": "synthetic-1", "source_mode": "SYNTHETIC_TEST", "snapshot_completeness": "COMPLETE", "is_stale": False, "market_phase": "LO", "price_unit": "VND_PER_SHARE", "quantity_unit": "SHARES", "is_valid_book": True}
    for side, prices, quantities in (("bid", [29750, 29700, 29650], [100000, 80000, 50000]), ("ask", [29800, 29850, 29900], [60000, 100000, 120000])):
        for level, (price, qty) in enumerate(zip(prices, quantities), 1): record[f"{side}_price_{level}"], record[f"{side}_qty_{level}"] = price, qty
    return record


def test_manual_kpi_example():
    metrics = liquidity_metrics(quote())
    assert metrics["spread_abs"] == 50 and metrics["mid_price"] == Decimal("29775")
    assert metrics["bid_depth_3"] == 230000 and metrics["ask_depth_3"] == 280000
    assert metrics["obi_3"] == Decimal(-50000) / 510000
    assert metrics["spread_bps"].quantize(Decimal(".0001")) == Decimal("16.7926")


def test_buy_sweep_and_partial_fill_examples():
    filled = simulate_sweep(quote(), "BUY", 100000)
    assert (filled["filled_qty"], filled["unfilled_qty"], filled["vwap_filled"], filled["slippage_abs"]) == (100000, 0, Decimal("29820"), Decimal("20"))
    partial = simulate_sweep(quote(), "BUY", 400000)
    assert (partial["filled_qty"], partial["unfilled_qty"], partial["coverage_ratio"]) == (280000, 120000, Decimal("0.7"))
    assert partial["vwap_filled"].quantize(Decimal(".0001")) == Decimal("29860.7143")


def test_buy_400_with_350_observed_depth_has_87_5_percent_coverage():
    record = quote()
    record["ask_qty_1"], record["ask_qty_2"], record["ask_qty_3"] = 100, 100, 150
    result = simulate_sweep(record, "BUY", 400)
    assert result["filled_qty"] == 350
    assert result["unfilled_qty"] == 50
    assert result["coverage_ratio"] == Decimal("0.875")
    assert len(result["level_fills"]) == 3
    assert all(fill["level"] <= 3 for fill in result["level_fills"])  # no fourth level is fabricated
    assert result["level_fills"][-1]["level"] == 3
    assert result["vwap_filled"] is not None
    assert "quantity exceeds the observed three-level depth" in result["warnings"]


def test_sell_sweep_uses_bid_levels():
    result = simulate_sweep(quote(), "SELL", 150000)
    assert result["filled_qty"] == 150000
    assert result["vwap_filled"].quantize(Decimal(".0001")) == Decimal("29733.3333")
    assert result["slippage_abs"].quantize(Decimal(".0001")) == Decimal("16.6667")


@pytest.mark.parametrize("field,value", [("ask_price_1", "ATO"), ("ask_price_1", None), ("ask_qty_1", -1)])
def test_invalid_book_is_rejected(field, value):
    record = quote(); record[field] = value
    result = simulate_sweep(record, "BUY", 100)
    assert not result["is_simulatable"] and result["filled_qty"] == 0


def test_stale_and_unverified_units_are_rejected():
    record = quote(); record["is_stale"] = True
    assert not assess_continuous_book(record).allowed
    record = quote(); record["price_unit"] = "UNVERIFIED"
    assert not assess_continuous_book(record).allowed


def test_empty_book_and_invalid_request_are_safe():
    record = quote()
    for side in ("bid", "ask"):
        for level in range(1, 4): record[f"{side}_qty_{level}"] = 0
    result = simulate_sweep(record, "BUY", 10)
    assert result["vwap_filled"] is None and result["slippage_abs"] is None
    assert liquidity_metrics(record)["obi_3"] is None
    with pytest.raises(ValueError): simulate_sweep(quote(), "BUY", 0)


def test_execution_invariants_across_sides_and_sizes():
    for side in ("BUY", "SELL"):
        for requested in (1, 50000, 100000, 400000):
            result = simulate_sweep(quote(), side, requested)
            assert 0 <= result["filled_qty"] <= requested
            assert result["unfilled_qty"] == requested - result["filled_qty"]
            if result["filled_qty"]:
                filled_prices = [fill["price"] for fill in result["level_fills"] if fill["filled_qty"]]
                assert min(filled_prices) <= result["vwap_filled"] <= max(filled_prices)
