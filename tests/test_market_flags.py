from data.market_flags import MarketFlagJoiner, parse_provider_time


def test_market_flag_is_joined_by_board_and_provider_time():
    joiner = MarketFlagJoiner()
    joiner.update(board="HOSE", trading_time="2026/11/18 09:15:00", flag="LO", received_at_utc="2026-11-18T02:15:01Z")
    result = joiner.phase_for(board="HOSE", quote_time="2026/11/18 09:20:00")
    assert result["market_phase"] == "LO"
    assert result["market_phase_source"] == "SSI_MARKET_FLAG"
    assert joiner.phase_for(board="HNX", quote_time="2026/11/18 09:20:00")["market_phase"] is None


def test_reconnect_clears_phase_until_a_new_flag_arrives():
    joiner = MarketFlagJoiner()
    joiner.update(board="HOSE", trading_time="2026/11/18 09:15:00", flag="LO")
    joiner.clear()
    result = joiner.phase_for(board="HOSE", quote_time="2026/11/18 09:20:00")
    assert result["market_phase"] is None
    assert result["market_phase_source"] == "UNKNOWN"


def test_provider_time_parser_handles_ssi_local_timestamp():
    parsed = parse_provider_time("2026/11/18 09:15:00")
    assert parsed is not None and parsed.utcoffset().total_seconds() == 7 * 3600
