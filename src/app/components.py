"""Reusable native widgets and presentational cards for the workspace."""
from __future__ import annotations
import base64
from functools import lru_cache
from html import escape
from datetime import datetime
from pathlib import Path
from contextvars import ContextVar
from app import state
from app.view_models import VN, local_time, load_quotes, make_view, history_points
from ssi_api.symbol_groups import VN30_SYMBOLS

ICON_PATHS = {
    "house": '<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
    "activity": '<path d="M2 12h5l3-9 4 18 3-9h5"/>',
    "play": '<path d="m7 3 15 9-15 9Z"/>',
    "history": '<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v6l4 2"/>',
    "chart-no-axes-column-increasing": '<path d="M4 20V13M10 20V8M16 20V3M22 20V10"/>',
    "bell": '<path d="M5 16V9a7 7 0 0 1 14 0v7l2 3H3ZM10 22h4"/>',
    "settings": '<path d="m10 2 4 0 1 4 4-1 2 4-3 3 3 3-2 4-4-1-1 4h-4l-1-4-4 1-2-4 3-3-3-3 2-4 4 1Z"/><circle cx="12" cy="12" r="3"/>',
    "spread": '<path d="M4 7h16l-4-4M20 17H4l4 4M20 7l-4 4M4 17l4-4"/>',
    "depth": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v12c0 4 16 4 16 0V5M4 11c0 4 16 4 16 0"/>',
    "obi": '<path d="M12 3v18M5 7h14M5 7l-4 9h8ZM19 7l-4 9h8ZM7 21h10"/>',
    "layers": '<path d="m12 2 10 6-10 6L2 8ZM2 13l10 6 10-6M2 18l10 6 10-6"/>',
    "shield": '<path d="m12 2 9 4v7c0 5-9 9-9 9s-9-4-9-9V6Z"/><path d="m7 12 3 3 6-6"/>',
    "bolt": '<path d="m14 2-11 13h8l-1 9 11-13h-8Z"/>',
}
NUMBER_FORMAT=ContextVar("lg_number_format",default="1.234,56")


def icon(name):
    return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON_PATHS.get(name, ICON_PATHS["layers"]) + '</svg>'


@lru_cache(maxsize=1)
def mascot_uri():
    path = Path(__file__).parent / "assets/mascot.png"
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def fmt(value, decimals=0, style=None):
    if value is None:
        return "—"
    style=style or NUMBER_FORMAT.get()
    text = f"{float(value):,.{decimals}f}"
    return text.translate(str.maketrans({",": ".", ".": ","})) if style == "1.234,56" else text


def header(st, ss):
    with st.container(key="lg_header"):
        cols = st.columns([2.3, 8.8, 1.9], gap="small")
        cols[0].markdown(f'<div class="lg-brand"><img src="{mascot_uri()}" alt="Linh vật LiquidityGuard">LiquidityGuard</div>', unsafe_allow_html=True)
        with cols[1]:
            tabs = st.columns([1.25,1.4,1.2,1.0,.9,.85,1.1], gap="small")
            for col, page, ico in zip(tabs, state.PAGES, state.ICONS):
                col.button(page, key=f"nav_{page}", type="primary" if ss["page"] == page else "tertiary", on_click=state.navigate, args=(ss,page), width="stretch")
        cols[2].markdown(f'<div class="lg-greeting">Xin chào, nhà đầu tư 👋<br><small>{datetime.now(VN):%d/%m · %H:%M} UTC+7 · SSI</small></div>', unsafe_allow_html=True)
    with st.container(key="lg_mobile_nav"):
        ss["mobile_page"]=ss["page"]
        st.selectbox("Điều hướng",state.PAGES,key="mobile_page",on_change=lambda:state.navigate(ss,ss["mobile_page"]),label_visibility="collapsed")


def controls(st, ss, universe):
    all_symbols = list(dict.fromkeys(row["symbol"] for row in universe)) or list(VN30_SYMBOLS)
    capture_date = universe[0].get("capture_date", "—") if universe else "—"
    with st.expander(f"⌕  {ss['selected_symbol']} · {ss['mode']} · {ss['trade_side']} {fmt(ss['requested_qty'])} CP   |   Tìm mã & bộ lọc", expanded=ss["page"]=="Market Pulse"):
        cols = st.columns([1.0,.9,1.0,1.4,2.0,1.2])
        kinds=["Stock","ALL"]+sorted({r.get("stock_type","UNKNOWN") for r in universe}-{"Stock"})
        kind=cols[0].selectbox("Loại mã",kinds,format_func=lambda x:"Cổ phiếu" if x=="Stock" else "Tất cả loại" if x=="ALL" else x,key="w_type")
        board = cols[1].selectbox("Sàn", ["Tất cả","HOSE","HNX","UPCOM"], key="w_board")
        group = cols[2].selectbox("Rổ chỉ số", ["Tất cả","VN30"], key="w_group")
        base=[r for r in universe if (kind=="ALL" or r.get("stock_type")==kind) and (board=="Tất cả" or r["board"]==board) and (group=="Tất cả" or r.get("index_group")==group)]
        sectors = sorted({r["sector"] for r in base})
        if ss.get("w_sector") not in ["Tất cả"]+sectors:ss["w_sector"]="Tất cả"
        sector = cols[3].selectbox("Ngành",["Tất cả"]+sectors, format_func=lambda x:"Chưa phân loại" if x=="UNCLASSIFIED" else x,key="w_sector")
        options = [r["symbol"] for r in base if sector=="Tất cả" or r["sector"]==sector]
        options = list(dict.fromkeys(options))
        if not options:
            options = all_symbols
        # Keep the selection coherent when an exchange/sector filter changes.
        if ss["selected_symbol"] not in options:
            state.select_symbol(ss,options[0])
        ss["w_symbol"] = ss["selected_symbol"]
        cols[4].selectbox("Tìm mã chứng khoán",options,key="w_symbol",on_change=lambda:state.select_symbol(ss,ss["w_symbol"]),help="Gõ ticker để tìm trong universe SSI")
        cols[5].button("☆ Thêm watchlist",width="stretch",on_click=lambda:ss.update(watchlist=list(dict.fromkeys(ss["watchlist"]+[ss["selected_symbol"]]))))
        st.caption(f"{len(options):,} mã trong bộ lọc · phạm vi capture {len(all_symbols):,} mã ngày {capture_date} · ngành thiếu dữ liệu được ghi Chưa phân loại.")
    count=sum(r.get("stock_type")=="Stock" for r in universe)
    if ss["page"]!="Market Pulse":
        st.button(f"▥ Mở danh mục đã capture · {count:,} cổ phiếu",key="open_market_universe",width="stretch",on_click=state.navigate,args=(ss,"Market Pulse"))


def kpis(st, vm, ss):
    metric, sim = vm["metrics"], vm["simulation"]
    obi = metric.get("obi_3")
    tilt = "Trung tính" if obi is None or abs(obi)<.05 else "Nghiêng về mua" if obi>0 else "Nghiêng về bán"
    items = [
        ("spread","Spread",fmt(metric.get("spread_bps"),1,ss["number_format"])+" bps",f"{fmt(metric.get('spread_abs'))} VND/CP"),
        ("depth","Bid Depth",fmt(metric.get("bid_depth_3")),"CP · ba mức chờ mua"),
        ("depth","Ask Depth",fmt(metric.get("ask_depth_3")),"CP · ba mức chờ bán"),
        ("obi","OBI",fmt(obi,3,ss["number_format"]),tilt if obi is not None else "Chưa xác minh"),
        ("layers","Coverage",fmt(sim["coverage_ratio"]*100,1)+"%" if sim else "—",f"Giả định {fmt(ss['requested_qty'])} CP"),
        ("shield","Data Trust","Verified" if vm["trust"]["allowed"] else "Blocked","Fixture" if vm["mode"]=="SYNTHETIC_TEST" else vm["trust"]["label"]),
    ]
    with st.container(key="lg_kpis"):
        cols = st.columns(6,gap="small")
    for i,(col,item) in enumerate(zip(cols,items)):
        ico,title,value,desc=item
        col.markdown(f'<div class="lg-kpi k{i+1}"><div class="lg-kpi-label">{icon(ico)}{title}</div><div class="lg-kpi-value">{escape(value)}</div><small>{escape(desc)}</small></div>',unsafe_allow_html=True)


def hero(st, vm, ss):
    complete = [bool(vm["quote"]), vm["trust"]["allowed"], bool(vm["simulation"]), bool(vm["simulation"])]
    steps = ["Dữ liệu đã tải", "Sổ lệnh hợp lệ", "Đã tính mô phỏng", "Có giải thích kết quả"]
    progress = int(sum(complete)/4*100)
    items = ''.join(f'<div class="lg-step {"" if passed else "pending"}"><i>{"✓" if passed else "○"}</i>{label}</div>' for passed,label in zip(complete,steps))
    st.markdown(f'''<div class="lg-hero"><div class="lg-hero-copy"><div class="lg-eyebrow" style="color:#f3c9dd">Your liquidity playground</div><h1>Execution Lab</h1><p>Thử một khối lượng,<br>hiểu rõ khả năng đáp ứng<br>trong 3 mức giá.</p><div class="lg-hero-badge"><span class="lg-pill">{ss['selected_symbol']} · {vm['trust']['label']}</span></div></div><img class="lg-mascot" src="{mascot_uri()}" alt="Linh vật LiquidityGuard"><div class="lg-progress"><strong>Execution Progress <span style="float:right">{progress}%</span></strong><div class="lg-progress-track"><span style="width:{progress}%"></span></div>{items}</div></div>''',unsafe_allow_html=True)
    mode_control(st,ss)


def mode_control(st,ss):
    with st.container(key="lg_mode"):
        ss.setdefault("w_mode",ss["mode"])
        st.segmented_control("Chế độ dữ liệu",["LIVE","REPLAY"],key="w_mode",selection_mode="single",on_change=lambda:state.change_mode(ss,ss["w_mode"] or "REPLAY"), label_visibility="collapsed")


def trade_strip(st, vm, ss):
    with st.container(key="lg_trade"):
        cols=st.columns([1.7,1.5,1.7,1.2,1.4,1.5,1.4],gap="small")
        cols[0].markdown('<div class="lg-section-title" style="font-size:15px;padding-top:12px">◎ Trade Simulation</div>',unsafe_allow_html=True)
        ss.setdefault("w_side",ss["trade_side"])
        cols[1].segmented_control("Chiều",["BUY","SELL"],key="w_side",on_change=lambda:ss.update(trade_side=ss["w_side"] or "BUY"),label_visibility="collapsed")
        ss.setdefault("w_quantity",ss["requested_qty"])
        cols[2].number_input("Số lượng CP",min_value=1,step=100,key="w_quantity",on_change=lambda:ss.update(requested_qty=ss["w_quantity"]),label_visibility="collapsed")
        cols[3].button("Mô phỏng",key="run_simulation",type="primary",disabled=not vm["trust"]["allowed"], on_click=lambda:ss.update(simulation_record={"snapshot_id":vm["snapshot_id"],"quote":dict(vm["quote"]),"mode":vm["mode"],"side":ss["trade_side"],"quantity":ss["requested_qty"]}),width="stretch")
        sim=vm["simulation"]
        cols[4].metric("VWAP · VND/CP",fmt(sim.get("vwap_filled"),1) if sim else "—")
        cols[5].metric("Đáp ứng · CP",fmt(sim["filled_qty"]) if sim else "—")
        cols[6].metric("Chưa đáp ứng · CP",fmt(sim["unfilled_qty"]) if sim else "—")
        if sim and sim["unfilled_qty"]:
            st.caption(f"⚠ Chỉ đáp ứng {fmt(sim['coverage_ratio']*100,1)}% trong ba mức; còn {fmt(sim['unfilled_qty'])} CP chưa có giá mô phỏng.")


def empty(st, message="Chưa đủ dữ liệu để vẽ", detail="Xem Alerts để kiểm tra đơn vị, trạng thái phiên và snapshot."):
    st.markdown(f'<div class="lg-empty"><strong>◇ {escape(message)}</strong><span>{escape(detail)}</span></div>',unsafe_allow_html=True)


def chart_card(st, title, key, fig=None, help_text=None):
    with st.container(key=f"lg_chart_{key}"):
        a,b=st.columns([5,1],gap="small")
        a.markdown(f'<div class="lg-chart-title">{icon("layers")}{escape(title)}</div>',unsafe_allow_html=True)
        with b.popover("ⓘ",help="Công thức và điều kiện dữ liệu",width="content"):
            st.caption(help_text or "Dùng cùng snapshot, chỉ tính trên ba mức L1–L3 đã xác minh.")
        if fig is None:
            empty(st)
        else:
            st.plotly_chart(fig,key=f"plot_{key}",width="stretch",config={"displayModeBar":False,"responsive":True})


def right_rail(st,ss,vm,rows,status,universe):
    with st.container(key="lg_card_quick"):
        st.markdown('<div class="lg-section-title">ϟ Quick Tasks</div>',unsafe_allow_html=True)
        st.button("▷  Mô phỏng mới  ›",key="quick_simulate",width="stretch",on_click=state.navigate,args=(ss,"Simulator"))
        def replay():
            state.change_mode(ss,"REPLAY"); state.navigate(ss,"Replay")
        st.button("↶  Phát lại một phiên  ›",key="quick_replay",width="stretch",on_click=replay)
        def compare():
            ss["compare_open"]=True; state.navigate(ss,"Charts")
        st.button("▱  So sánh thanh khoản  ›",key="quick_compare",width="stretch",on_click=compare)
    with st.container(key="lg_card_watchlist"):
        st.markdown('<div class="lg-section-title">▥ Watchlist</div>',unsafe_allow_html=True)
        from app.market_data import MARKET_DB
        from data.market_catalog import load_latest
        historical=load_latest(MARKET_DB)
        st.caption("Giá đóng cửa SSI đã lưu được ghi REST; book mô phỏng dùng chế độ đang chọn.")
        allowed={row["symbol"] for row in universe}
        favorites=[symbol for symbol in ss["watchlist"] if symbol in allowed]
        if len(favorites)>6:
            page=st.selectbox("Trang yêu thích",list(range((len(favorites)+5)//6)),format_func=lambda x:f"{x+1} / {(len(favorites)+5)//6}",key="watchlist_page",label_visibility="collapsed")
        else:page=0
        for symbol in favorites[page*6:page*6+6]:
            choices=load_quotes(ss["mode"],symbol)
            quote=choices[-1] if choices else None
            view=make_view(quote,ss["mode"],status,ss["trade_side"],ss["requested_qty"])
            board=next((r["board"] for r in universe if r["symbol"]==symbol),"—")
            col,text=st.columns([1.1,1.9])
            col.button(f"☆ {symbol}",key=f"watch_{symbol}",on_click=state.select_symbol,args=(ss,symbol),width="stretch")
            daily=historical.get(symbol)
            if daily:
                from app.market_data import number
                display_price=fmt(number(daily.get("close")))
                detail="REST · "+str(daily.get("trading_date") or "—")
            else:
                display_price=fmt(view["metrics"].get("mid_price"))
                detail=("DEMO · " if ss["mode"]=="SYNTHETIC_TEST" else "")+local_time(quote.get("quote_time_vn"),True) if quote else "Chưa có dữ liệu giao dịch"
            text.markdown(f'<div class="lg-subtle" style="text-align:right">{board} · {display_price}<br>{escape(detail)}</div>',unsafe_allow_html=True)
        st.caption(f"{len(favorites)} mã yêu thích · trong phạm vi {len(allowed)} mã đã capture")
        st.button("Xem 230 mã đã capture",key="watchlist_all_market",width="stretch",on_click=state.navigate,args=(ss,"Market Pulse"))
    with st.container(key="lg_card_session"):
        points=history_points(rows,ss["mode"],status)
        start=rows[0].get("quote_time_vn") if rows else None; end=rows[-1].get("quote_time_vn") if rows else None
        from app.view_models import parse_time
        span=(parse_time(end)-parse_time(start)).total_seconds() if start and end and parse_time(start) and parse_time(end) else 0
        avg_spread=sum(p["spread_bps"] for p in points)/len(points) if points else None
        obi_points=[p["obi_3"] for p in points if p.get("obi_3") is not None]
        avg_obi=sum(obi_points)/len(obi_points) if obi_points else None
        st.markdown('<div class="lg-section-title">▣ Session Snapshot</div>',unsafe_allow_html=True)
        st.caption(f"Cửa sổ quan sát {fmt(span)} giây")
        for label,value in [("Thời gian",f"{local_time(start,True)} → {local_time(end,True)}"),("Avg. spread",fmt(avg_spread,2)+" bps"),("Avg. OBI",fmt(avg_obi,3)),("Snapshot hợp lệ",f"{len(points)}/{len(rows)}")]:
            st.markdown(f'<div class="lg-health"><span>{label}</span><b>{value}</b></div>',unsafe_allow_html=True)
    with st.container(key="lg_card_health"):
        st.markdown('<div class="lg-section-title">♧ Data Health</div>',unsafe_allow_html=True)
        quote=vm["quote"] or {}
        for label,value in [("Nguồn","SSI FastConnect"),("Chế độ",ss["mode"]),("WS",str(status.get("state","offline")).upper()),("Giá",quote.get("price_unit","—")),("Khối lượng",quote.get("quantity_unit","—")),("Phiên",quote.get("market_phase") or "UNKNOWN"),("Book", "Hợp lệ" if quote.get("is_valid_book") else "Chưa xác minh"),("Quote age",fmt(vm["trust"]["age_seconds"])+" s"),("Cập nhật",local_time(quote.get("quote_time_vn"),True))]:
            st.markdown(f'<div class="lg-health"><span>{label}</span><b>{escape(str(value))}</b></div>',unsafe_allow_html=True)
        st.button("Chi tiết Data Trust  ›",key="open_trust",width="stretch",on_click=state.navigate,args=(ss,"Alerts"))


def execution_sidebar(st, ss):
    """Locked-spec navigation used only by Execution Lab."""
    with st.container(key="lg_exec_sidebar"):
        st.markdown(
            f'<div class="lg-exec-brand"><img src="{mascot_uri()}" alt="LiquidityGuard mascot">'
            '<div><strong>LiquidityGuard</strong><span>Liquidity Intelligence for<br>Smarter Execution</span></div></div>',
            unsafe_allow_html=True,
        )
        entries = [
            ("⌂", "Tổng quan", "Dashboard"),
            ("⌁", "Mô phỏng lệnh", "Simulator"),
            ("▷", "Replay phiên", "Replay"),
            ("▥", "So sánh mã", "Charts"),
            ("♧", "Data Trust", "Alerts"),
            ("♢", "Cảnh báo", "Alerts"),
            ("⚙", "Cài đặt", "Settings"),
        ]
        seen = set()
        for index, (glyph, label, page) in enumerate(entries):
            key = f"nav_{page}" if page not in seen else f"exec_nav_{index}_{page}"
            seen.add(page)
            st.button(
                f"{glyph}   {label}", key=key,
                type="primary" if ss["page"] == page and (page != "Alerts" or label == "Data Trust") else "tertiary",
                on_click=state.navigate, args=(ss, page), width="stretch",
            )
        st.markdown('<div class="lg-exec-clouds"><i></i><i></i><i></i></div>', unsafe_allow_html=True)


def execution_topbar(st, ss, universe):
    """Mode/search/date/session controls sharing the global workspace state."""
    from app.view_models import parse_time
    symbols = [row["symbol"] for row in universe]
    rows = load_quotes(ss["mode"], ss["selected_symbol"])
    dates = sorted({parse_time(row.get("quote_time_vn") or row.get("received_at_utc")).date().isoformat()
                    for row in rows if parse_time(row.get("quote_time_vn") or row.get("received_at_utc"))})
    with st.container(key="lg_exec_topbar"):
        cols = st.columns([2.45, 2.15, 1.35, 1.0, .45, 1.05], gap="small")
        ss["exec_mode"] = ss["mode"]
        cols[0].segmented_control(
            "Mode", ["LIVE", "REPLAY"], key="exec_mode",
            on_change=lambda: state.change_mode(ss, ss["exec_mode"] or "REPLAY"),
            label_visibility="collapsed",
        )
        if ss["selected_symbol"] not in symbols and symbols:
            state.select_symbol(ss, symbols[0])
        ss["exec_search"] = ss["selected_symbol"]
        cols[1].selectbox(
            "Tìm mã", symbols, key="exec_search", label_visibility="collapsed",
            on_change=lambda: state.select_symbol(ss, ss["exec_search"]),
        )
        if ss["mode"] == "REPLAY" and dates:
            if ss.get("selected_date") not in dates:
                ss["selected_date"] = dates[-1]
            ss["exec_date"] = ss["selected_date"]
            cols[2].selectbox(
                "Ngày", dates, key="exec_date", label_visibility="collapsed",
                format_func=lambda value: datetime.fromisoformat(value).strftime("%d/%m/%Y"),
                on_change=lambda: ss.update(selected_date=ss["exec_date"], snapshot_id=None, simulation_record=None),
            )
        else:
            latest = dates[-1] if dates else datetime.now(VN).date().isoformat()
            cols[2].markdown(f'<div class="lg-exec-date">▣ {datetime.fromisoformat(latest):%d/%m/%Y}</div>', unsafe_allow_html=True)
        ss["exec_session"] = ss.get("selected_session", "Cả ngày")
        cols[3].selectbox(
            "Phiên", ["Cả ngày", "Phiên sáng", "Phiên chiều"], key="exec_session",
            label_visibility="collapsed", on_change=lambda: state.change_session(ss, ss["exec_session"]),
        )
        cols[4].button("♢", key="exec_bell", help="Cảnh báo dữ liệu", on_click=state.navigate, args=(ss, "Alerts"), width="stretch")
        cols[5].markdown('<div class="lg-exec-greeting"><b>Xin chào!</b><span>SSI · Chỉ đọc</span></div>', unsafe_allow_html=True)


def execution_hero(st, vm, ss):
    mode_label = escape(vm["trust"]["label"])
    st.markdown(
        f'''<section class="lg-exec-hero">
          <div class="lg-exec-hero-copy"><h1>Execution Lab</h1>
          <p>Hiểu thanh khoản và kiểm chứng quyết định giao dịch:<br><b>Liệu một lệnh có thể được đáp ứng trong 3 mức giá?</b></p>
          <div class="lg-exec-tags"><span>⚡ Ước tính khả năng đáp ứng</span><span>◎ Đo tác động giá</span><span>◈ Hỗ trợ quyết định</span></div>
          <small>{escape(ss['selected_symbol'])} · {mode_label}</small></div>
          <img src="{mascot_uri()}" alt="Linh vật gấu mèo LiquidityGuard với laptop tím">
          <i class="cloud c1"></i><i class="cloud c2"></i>
        </section>''', unsafe_allow_html=True,
    )


def execution_controls(st, vm, ss, universe):
    symbols = [row["symbol"] for row in universe]
    with st.container(key="lg_exec_controls"):
        cols = st.columns([1.55, 1.45, 1.35, 1.55, 1.65], gap="small")
        cols[0].markdown('<div class="lg-exec-control-title">◎ <b>Mô phỏng lệnh</b></div>', unsafe_allow_html=True)
        ss["exec_side"] = ss["trade_side"]
        def side_changed():
            ss["trade_side"] = ss["exec_side"] or "BUY"
            ss.pop("simulation_record", None)
        cols[1].segmented_control("Chiều", ["BUY", "SELL"], key="exec_side", on_change=side_changed, label_visibility="collapsed")
        ss["exec_symbol"] = ss["selected_symbol"]
        cols[2].selectbox("Mã", symbols, key="exec_symbol", on_change=lambda: state.select_symbol(ss, ss["exec_symbol"]), label_visibility="collapsed")
        ss["exec_quantity"] = int(ss["requested_qty"])
        def quantity_changed():
            ss["requested_qty"] = int(ss["exec_quantity"])
            ss.pop("simulation_record", None)
        cols[3].number_input("Khối lượng (CP)", min_value=1, max_value=100_000_000, step=1, key="exec_quantity", on_change=quantity_changed, label_visibility="collapsed")
        def freeze():
            ss["simulation_record"] = {
                "snapshot_id": vm["snapshot_id"], "quote": dict(vm["quote"]),
                "mode": vm["mode"], "symbol": ss["selected_symbol"],
                "side": ss["trade_side"], "quantity": int(ss["requested_qty"]),
            }
        cols[4].button("▷  Mô phỏng ngay", key="exec_run_simulation", type="primary", disabled=not vm["trust"]["allowed"], on_click=freeze, width="stretch")


def execution_results(st, vm, ss):
    sim = vm.get("simulation")
    values = {
        "VWAP": fmt(sim.get("vwap_filled"), 1) if sim else "—",
        "Đáp ứng · CP": fmt(sim.get("filled_qty")) if sim else "—",
        "Chưa đáp ứng · CP": fmt(sim.get("unfilled_qty")) if sim else "—",
        "Price impact · bps": fmt(sim.get("slippage_bps"), 2) if sim and sim.get("slippage_bps") is not None else "—",
        "Coverage": fmt(sim.get("coverage_ratio") * 100, 1) + "%" if sim else "—",
    }
    cells = ''.join(f'<div><span>{escape(label)}</span><b>{escape(value)}</b></div>' for label, value in values.items())
    st.markdown(f'<section class="lg-exec-results"><header>◈ <b>Kết quả mô phỏng</b><small>Không phải lệnh thật</small></header>{cells}</section>', unsafe_allow_html=True)


def execution_insight(st, vm, ss):
    sim = vm.get("simulation")
    if not sim:
        reasons = " · ".join(vm["trust"].get("reasons") or ["Snapshot chưa đủ điều kiện"])
        text = f"Không thể mô phỏng snapshot này: {reasons}. Có thể xem dữ liệu quan sát hoặc chuyển sang REPLAY hợp lệ."
        notes = ["Mô phỏng đang khóa", "Không tự điền market phase", "Không dự đoán L4"]
        tone = "blocked"
    else:
        side = "mua" if sim["side"] == "BUY" else "bán"
        coverage = fmt(sim["coverage_ratio"] * 100, 1)
        text = f"Với lệnh {side} giả định {fmt(sim['requested_qty'])} CP {ss['selected_symbol']}, sổ lệnh L1–L3 ghi nhận khả năng đáp ứng {coverage}% ({fmt(sim['filled_qty'])} CP)."
        if sim["unfilled_qty"]:
            text += f" Còn {fmt(sim['unfilled_qty'])} CP chưa đáp ứng trong phạm vi quan sát; không ước lượng giá L4."
        else:
            text += " Toàn bộ khối lượng nằm trong độ sâu L1–L3 đang quan sát."
        levels = sum(fill["filled_qty"] > 0 for fill in sim["level_fills"])
        notes = [f"Dùng {levels} mức giá", f"Impact {fmt(sim.get('slippage_bps'),2)} bps", "Không bảo đảm khớp thật"]
        tone = "ok" if not sim["unfilled_qty"] else "warning"
    note_html = ''.join(f'<span>✓ {escape(note)}</span>' for note in notes)
    st.markdown(f'<section class="lg-exec-insight {tone}"><div class="bulb">◉</div><p>{escape(text)}</p><aside>{note_html}</aside></section>', unsafe_allow_html=True)


def execution_right_rail(st, ss, vm, rows, status, universe):
    from app.market_data import MARKET_DB
    from data.market_catalog import load_latest
    from app.view_models import observation_history_points, history_points, parse_time
    historical = load_latest(MARKET_DB)
    allowed = {row["symbol"] for row in universe}
    favorites = [symbol for symbol in ss["watchlist"] if symbol in allowed][:5]
    with st.container(key="lg_exec_watchlist"):
        head = st.columns([3, 1])
        head[0].markdown('<div class="lg-exec-rail-title">☆ Watchlist của bạn</div>', unsafe_allow_html=True)
        head[1].button("Xem tất cả", key="exec_watch_all", on_click=state.navigate, args=(ss, "Market Pulse"), width="stretch")
        st.caption("Giá REST đã lưu; trạng thái book theo mode đang chọn.")
        for symbol in favorites:
            quote_rows = load_quotes(ss["mode"], symbol)
            quote = quote_rows[-1] if quote_rows else None
            view = make_view(quote, ss["mode"], status, ss["trade_side"], ss["requested_qty"])
            summary = historical.get(symbol, {})
            price = summary.get("close")
            label = "Đạt gate" if view["trust"]["allowed"] else "Chưa đánh giá"
            cols = st.columns([1.1, 1, 1.35])
            cols[0].button(f"☆ {symbol}", key=f"exec_watch_{symbol}", on_click=state.select_symbol, args=(ss, symbol), width="stretch")
            cols[1].markdown(f'<b class="lg-exec-watch-price">{fmt(price) if price is not None else "—"}</b>', unsafe_allow_html=True)
            provenance = "REST · " + str(summary.get("trading_date") or "—") if summary else "Không có giá REST"
            cols[2].markdown(f'<span class="lg-exec-watch-state">{escape(label)}</span><small>{escape(provenance)}</small>', unsafe_allow_html=True)
    with st.container(key="lg_exec_session"):
        valid = history_points(rows, ss["mode"], status)
        observed = observation_history_points(rows)
        start = rows[0].get("quote_time_vn") if rows else None
        end = rows[-1].get("quote_time_vn") if rows else None
        span = (parse_time(end) - parse_time(start)).total_seconds() if start and end and parse_time(start) and parse_time(end) else 0
        spreads = [point["spread_bps"] for point in observed if point.get("spread_bps") is not None]
        obis = [point["obi_3"] for point in observed if point.get("obi_3") is not None]
        st.markdown('<div class="lg-exec-rail-title">▥ Session Snapshot</div>', unsafe_allow_html=True)
        st.caption("Tổng quan phạm vi dữ liệu đang chọn")
        for label, value in [
            ("Thời gian", f"{local_time(start,True)} – {local_time(end,True)}"),
            ("Cửa sổ quan sát", f"{fmt(span)} giây"),
            ("Avg. spread", fmt(sum(spreads)/len(spreads),2)+" bps" if spreads else "—"),
            ("Avg. OBI", fmt(sum(obis)/len(obis),3) if obis else "—"),
            ("Snapshot đạt điều kiện", f"{len(valid)} / {len(rows)}"),
        ]:
            st.markdown(f'<div class="lg-exec-row"><span>{escape(label)}</span><b>{escape(value)}</b></div>', unsafe_allow_html=True)
    with st.container(key="lg_exec_trust"):
        quote = vm.get("quote") or {}
        synthetic = ss["mode"] == "SYNTHETIC_TEST"
        checks = [
            (quote.get("price_unit") == "VND_PER_SHARE" and quote.get("quantity_unit") == "SHARES", "Đơn vị fixture TEST" if synthetic else "Đơn vị SSI đã xác minh"),
            (bool(quote.get("complete_book_verified")), "Book fixture hoàn chỉnh" if synthetic else "Snapshot full-book"),
            (quote.get("market_phase") == "LO" if synthetic else quote.get("market_phase_source") == "SSI_MARKET_FLAG", "Phase fixture TEST" if synthetic else "market.flag đúng snapshot"),
            (bool(quote.get("raw_event_id")), "Fixture lineage tồn tại" if synthetic else "Raw lineage tồn tại"),
            (status.get("state") == "online" if ss["mode"] == "LIVE" else True, "Kết nối phù hợp mode"),
        ]
        st.markdown(f'<div class="lg-exec-rail-title">♧ Data Trust <em>{escape(vm["trust"]["label"])}</em></div>', unsafe_allow_html=True)
        for passed, label in checks:
            st.markdown(f'<div class="lg-exec-check {"pass" if passed else "fail"}">{"✓" if passed else "!"} {escape(label)}</div>', unsafe_allow_html=True)
        st.button("Chi tiết Data Trust", key="exec_open_trust", on_click=state.navigate, args=(ss, "Alerts"), width="stretch")
