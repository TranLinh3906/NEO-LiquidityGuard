import json

from data.ohlc_history import append_bars, intraday_liquidity_windows, normalize_bar, summarize


def test_ohlc_normalization_and_idempotent_append(tmp_path):
    raw = {"symbol": "FPT", "tradingDate": "2026/11/18", "open": "100", "high": "110", "low": "95", "close": "108", "volume": "1000", "value": "108000"}
    bar = normalize_bar(raw, symbol="FPT", timeframe="1d")
    path = tmp_path / "ohlc.jsonl"
    assert append_bars(path, [bar]) == 1
    assert append_bars(path, [bar]) == 0
    stats = summarize([bar])[0]
    assert stats["total_volume"] == 1000 and stats["price_change_pct"] == 8.0


def test_intraday_liquidity_buckets_rank_value():
    bars = [
        normalize_bar({"symbol": "FPT", "tradingDate": "2026/11/18 09:01:00", "volume": 10, "value": 100}, symbol="FPT", timeframe="1m"),
        normalize_bar({"symbol": "FPT", "tradingDate": "2026/11/18 09:29:00", "volume": 30, "value": 300}, symbol="FPT", timeframe="1m"),
    ]
    rows = intraday_liquidity_windows(bars)
    assert rows[0]["time_bucket"] == "09:00" and rows[0]["value"] == 400
