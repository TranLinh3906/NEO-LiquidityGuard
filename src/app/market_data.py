"""Market-wide availability and real daily-price views, independent of L3 mode."""
from __future__ import annotations
from collections import Counter
import json
import math
from pathlib import Path
import sqlite3
from data.market_catalog import load_latest,load_symbol
from app.view_models import ROOT

MARKET_DB=ROOT/"data/processed/market_catalog.sqlite"


def number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (TypeError,ValueError):return None


def availability(database=None,history_path=None):
    db=Path(database or ROOT/"data/processed/quotes.sqlite")
    quotes={}
    if db.exists():
        with sqlite3.connect(f"file:{db}?mode=ro",uri=True) as connection:
            quotes=dict(connection.execute("SELECT symbol,COUNT(*) FROM quotes WHERE provider='SSI' AND source='SSI_FASTCONNECT' AND source_mode='LIVE' GROUP BY symbol"))
    daily=Counter();minute=Counter()
    path=Path(history_path or ROOT/"data/processed/ohlc_history.jsonl")
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():continue
                try:row=json.loads(line)
                except ValueError:continue
                if row.get("provider")!="SSI" or row.get("source_mode")!="HISTORICAL":continue
                target=daily if row.get("timeframe")=="1d" else minute if row.get("timeframe")=="1m" else None
                if target is not None:target[row.get("symbol")]+=1
    return {"quotes":quotes,"daily":dict(daily),"minute":dict(minute)}


def market_rows(universe, latest, counts):
    output=[]
    for item in universe:
        symbol=item["symbol"];summary=latest.get(symbol,{})
        output.append({
            "Mã":symbol,"Sàn":item["board"],"Tên doanh nghiệp":item.get("company_name") or "—",
            "Ngành":item["sector"] if item["sector"]!="UNCLASSIFIED" else "Chưa phân loại",
            "Loại":item.get("stock_type","UNKNOWN"),
            "Rổ chỉ số": item.get("index_group") or "—",
            "Giá đóng cửa SSI":number(summary.get("close")),
            "Thay đổi %":number(summary.get("price_change_pct")),
            "KL khớp SSI":number(summary.get("volume")),"GTGD SSI":number(summary.get("value")),
            "Giá tham chiếu SSI":number(item.get("ref_price")),
            "Ngày giao dịch":str(summary.get("trading_date") or item.get("trading_date") or "—"),
            "Dữ liệu": "Có giao dịch tổng hợp" if summary else "Chỉ metadata/tham chiếu",
            "Quote L3 đã thu":counts["quotes"].get(symbol,0),
            "Nến daily":counts["daily"].get(symbol,0),"Nến 1m":counts["minute"].get(symbol,0),
        })
    return sorted(output,key=lambda r:(r["Giá đóng cửa SSI"] is None,r["Mã"]))


def render_selected(st,ss,*,key="selected_market"):
    """Show real history even when there is no three-level simulation fixture."""
    import plotly.graph_objects as go
    from app import charts
    from app.components import fmt
    path=MARKET_DB
    @st.cache_data(show_spinner=False)
    def cached(symbol,mtime):return load_symbol(symbol,path)
    rows=cached(ss["selected_symbol"],path.stat().st_mtime_ns if path.exists() else 0)
    if not rows:return
    row=rows[-1]
    with st.container(key="lg_card_"+key):
        st.subheader(f"Dữ liệu giao dịch SSI · {ss['selected_symbol']}")
        st.caption(f"REST đã lưu · phiên {row['trading_date']} · nguồn SSI_FASTCONNECT · độc lập với chế độ mô phỏng {ss['mode']}")
        cols=st.columns(4)
        for col,label,value in zip(cols,["Giá đóng cửa SSI","Thay đổi %","Khối lượng khớp SSI","Giá trị giao dịch SSI"],[number(row.get("close")),number(row.get("price_change_pct")),number(row.get("volume")),number(row.get("value"))]):
            col.metric(label,fmt(value,2 if label=="Thay đổi %" else 0))
        if len(rows)>1:
            fig=go.Figure(go.Scatter(x=[r["trading_date"] for r in rows],y=[number(r.get("close")) for r in rows],mode="lines+markers",name="Đóng cửa",line_color=charts.PURPLE))
            st.plotly_chart(charts.style(fig,210),width="stretch",key=key+"_close")
        st.caption("Giá/khối lượng/giá trị giữ theo phản hồi SSI. Phần này thống kê giao dịch đã khớp; mô phỏng L3 vẫn theo kiểm chứng riêng.")
