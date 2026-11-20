from data.market_catalog import normalize_summary,save_summaries,load_latest
from app.market_data import market_rows


def test_sdk_summary_aliases_and_missing_values_preserved(tmp_path):
    source={"symbol":"HPG","trading_date":"2026/11/18","close_price":20450,"total_match":21967200,"total_match_value":454061075000,"price_change_percent":-2.62}
    parsed=normalize_summary(source)
    assert parsed["price_change_pct"]==-2.62 and parsed["close"]==20450
    path=tmp_path/"market.sqlite"
    save_summaries([source],path,raw_event_id="e1");save_summaries([source],path,raw_event_id="e1")
    latest=load_latest(path)
    assert len(latest)==1 and latest["HPG"]["volume"]==21967200
    assert latest["HPG"]["source_mode"]=="HISTORICAL_REST"
    assert normalize_summary({"symbol":"EMPTY","trading_date":"2026/11/18"})["volume"] is None


def test_market_table_keeps_all_symbols_without_synthetic_fallback():
    universe=[{"symbol":symbol,"board":"HOSE","sector":"UNCLASSIFIED","stock_type":"Stock","ref_price":None} for symbol in ("HPG","EMPTY")]
    rows=market_rows(universe,{"HPG":{"close":20450,"volume":0,"value":0,"trading_date":"2026/11/18"}},{"quotes":{},"daily":{},"minute":{}})
    assert len(rows)==2
    empty=next(r for r in rows if r["Mã"]=="EMPTY")
    valid=next(r for r in rows if r["Mã"]=="HPG")
    assert empty["Giá đóng cửa SSI"] is None and empty["KL khớp SSI"] is None
    assert valid["KL khớp SSI"]==0  # reported zero and missing remain distinct
    assert empty["Quote L3 đã thu"]==0
