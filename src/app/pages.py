"""Seven functional workspace pages built from the existing backend."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
import csv
import io
import json
from pathlib import Path
from app import charts, state
from app.components import (
    chart_card, empty, fmt, hero, kpis, trade_strip,
    execution_hero, execution_controls, execution_results,
    execution_insight, execution_right_rail,
)
from app.view_models import ROOT, local_time, make_view, history_points, is_observable_book, observation_history_points, load_quotes, parse_time
from finance.explain import explain


def dashboard(st,ss,vm,rows,status):
    if not vm["quote"]:
        from app.market_data import render_selected
        render_selected(st,ss,key="dashboard_actual_market")
    kpis(st,vm,ss)
    hero(st,vm,ss)
    trade_strip(st,vm,ss)
    quote,sim=vm["quote"],vm["simulation"]
    enabled=vm["trust"]["allowed"]
    observable=is_observable_book(quote)
    if not enabled:
        reasons=" · ".join(vm["trust"].get("reasons") or ["Snapshot chưa vượt qua Data Trust"])
        if observable:
            st.warning(f"Mô phỏng đang bị khóa: {reasons}. Biểu đồ quan sát book vẫn được hiển thị và không được xem là LIVE đã xác minh phase.")
        else:
            st.warning(f"Biểu đồ sổ lệnh đang bị khóa: {reasons}")
        if ss["mode"]=="LIVE" and rows:
            st.button(
                "Mở snapshot hợp lệ đã lưu ở REPLAY", key="dashboard_open_valid_replay",
                on_click=state.change_mode, args=(ss,"REPLAY"), type="primary",
            )
    cols=st.columns(3,gap="small")
    with cols[0]: chart_card(st,"Depth Mirror · Quan sát","depth",charts.depth(quote) if observable else None, "Được vẽ khi book, đơn vị và ba mức hợp lệ. Thiếu market.flag vẫn được ghi rõ và tiếp tục khóa mô phỏng.")
    with cols[1]: chart_card(st,"Sweep Allocation","sweep",charts.sweep(sim) if sim else None,"L1, L2, L3 và phần Chưa đáp ứng; chỉ ba mức giá.")
    with cols[2]: chart_card(st,"Coverage Curve","coverage",charts.curve(quote,ss["trade_side"],ss["requested_qty"]) if enabled else None,"Coverage = min(depth, Q) / Q × 100. Giữ book cố định: coverage không tăng khi Q tăng.")
    points=observation_history_points(rows)
    cols=st.columns(2,gap="small")
    with cols[0]: chart_card(st,"Spread Timeline · Quan sát","spread",charts.timeline(points,"spread_bps") if points else None,"Chuỗi quan sát có đơn vị/book hợp lệ; không thay thế market phase. Đường bị ngắt khi thiếu quan sát quá 60 giây.")
    with cols[1]: chart_card(st,"OBI Timeline · Quan sát","obi",charts.timeline(points,"obi_3",bar=True) if points else None,"Chỉ mô tả lượng chờ trong book; không phải tín hiệu mua/bán và không mở khóa mô phỏng.")
    with st.expander("ⓘ Công thức & giới hạn mô phỏng"):
        if sim: st.info(explain(vm["metrics"],sim))
        st.write("Mua quét Ask1 → Ask3; bán quét Bid1 → Bid3. VWAP chỉ tính trên lượng đáp ứng; phần còn thiếu không có giá ngoại suy. Mô hình chưa bao gồm hàng đợi, phí, thuế và biến động trong khi thực hiện.")
        st.caption(f"Snapshot ID: {vm['snapshot_id'] or '—'} · {local_time((quote or {}).get('quote_time_vn'))} UTC+7")


def simulator(st,ss,vm,rows,status,universe):
    """Locked Execution Lab: one snapshot drives every result and chart."""
    frozen=ss.get("simulation_record")
    if (frozen and frozen.get("mode")==ss["mode"] and frozen.get("symbol")==ss["selected_symbol"]
            and frozen.get("snapshot_id")==vm["snapshot_id"]):
        vm=make_view(frozen["quote"],frozen["mode"],status,frozen["side"],frozen["quantity"],stale_seconds=ss["stale_seconds"])
    main,right=st.columns([986,415],gap="small")
    with main:
        execution_hero(st,vm,ss)
        execution_controls(st,vm,ss,universe)
        execution_results(st,vm,ss)
        execution_insight(st,vm,ss)
        quote,sim=vm.get("quote"),vm.get("simulation")
        observable=is_observable_book(quote)
        points=observation_history_points(rows)
        first=st.columns(3,gap="small")
        with first[0]: chart_card(st,"Depth Mirror · Quan sát","exec_depth",charts.depth(quote) if observable else None,"Giá và khối lượng L1–L3 của cùng snapshot; [0,0] là mức trống.")
        with first[1]: chart_card(st,"Sweep Allocation","exec_sweep",charts.sweep(sim) if sim else None,"L1–L3 và phần chưa đáp ứng; tổng các phần bằng đúng Q.")
        with first[2]: chart_card(st,"Coverage Curve","exec_coverage",charts.curve(quote,vm["side"],vm["quantity"]) if sim else None,"Coverage không tăng khi Q tăng trên cùng book; đường dọc là Q đang chọn.")
        second=st.columns(2,gap="small")
        with second[0]: chart_card(st,"Spread Timeline · Quan sát","exec_spread",charts.timeline(points,"spread_bps") if points else None,"Spread bps của cùng mã/mode/cửa sổ; đường ngắt tại gap lớn hơn 60 giây.")
        with second[1]: chart_card(st,"OBI Timeline · Quan sát","exec_obi",charts.timeline(points,"obi_3",bar=True) if points else None,"OBI trong [-1,1]; không phải tín hiệu mua hoặc bán.")
        with st.expander("▣  Công thức & giới hạn mô phỏng",expanded=False):
            st.markdown("""
            **Spread:** `Ask1 − Bid1`; **Spread bps:** `Spread / Mid × 10.000`  
            **Depth₃:** `Σ Qty(L1…L3)`; **OBI:** `(BidDepth₃ − AskDepth₃) / (BidDepth₃ + AskDepth₃)`  
            **Coverage:** `Filled / Q × 100%`; **VWAP filled:** `Σ(Priceᵢ × Filledᵢ) / Filled`  
            **Impact BUY:** `(VWAP − Ask1) / Ask1 × 10.000`; **Impact SELL:** `(Bid1 − VWAP) / Bid1 × 10.000`.

            Mô hình không gồm queue priority, thanh khoản ẩn, thay đổi book trong khi giả lập, phí và thuế. Phần chưa đáp ứng không được ngoại suy sang L4.
            """)
            q=vm.get("quote") or {}; sim=vm.get("simulation")
            st.caption(f"Nguồn: SSI FastConnect · mode {vm['mode']} · snapshot {vm['snapshot_id'] or '—'} · {local_time(q.get('quote_time_vn'))} UTC+7 · policy verification v1")
            if sim:
                payload={"provider":"SSI_FASTCONNECT","mode":vm["mode"],"symbol":ss["selected_symbol"],"snapshot_id":vm["snapshot_id"],"quote_time":q.get("quote_time_vn"),"side":sim["side"],"Q":sim["requested_qty"],"filled":sim["filled_qty"],"unfilled":sim["unfilled_qty"],"VWAP":sim["vwap_filled"],"coverage":sim["coverage_ratio"],"impact":sim["slippage_bps"],"evidence":q.get("unit_evidence_ref"),"validation":vm["trust"]["label"]}
                downloads=st.columns(2)
                downloads[0].download_button("↓ Xuất JSON",json.dumps(payload,ensure_ascii=False,indent=2,default=str),file_name=f"{vm['mode']}_{ss['selected_symbol']}_simulation.json",mime="application/json",width="stretch")
                buffer=io.StringIO(); writer=csv.DictWriter(buffer,fieldnames=list(payload)); writer.writeheader(); writer.writerow(payload)
                downloads[1].download_button("↓ Xuất CSV",buffer.getvalue(),file_name=f"{vm['mode']}_{ss['selected_symbol']}_simulation.csv",mime="text/csv",width="stretch")
    with right:
        execution_right_rail(st,ss,vm,rows,status,universe)


def market_pulse(st,ss,vm,rows,status,universe):
    with st.container(key="lg_card_pulse"):
        st.subheader("Market Pulse")
        from app.market_data import MARKET_DB,availability,market_rows,render_selected
        from data.market_catalog import load_latest
        @st.cache_data(show_spinner=False)
        def indexed_counts(signature):return availability()
        data_paths=[ROOT/"data/processed/quotes.sqlite",ROOT/"data/processed/ohlc_history.jsonl"]
        signature=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in data_paths if p.exists())
        counts=indexed_counts(signature)
        latest=load_latest(MARKET_DB)
        all_rows=market_rows(universe,latest,counts)
        kind=ss.get("w_type","Stock");board=ss.get("w_board","Tất cả");sector=ss.get("w_sector","Tất cả");group=ss.get("w_group","Tất cả")
        filtered=[row for row in all_rows if (kind=="ALL" or row["Loại"]==kind) and (board=="Tất cả" or row["Sàn"]==board) and (group=="Tất cả" or row["Rổ chỉ số"]==group) and (sector=="Tất cả" or row["Ngành"]==("Chưa phân loại" if sector=="UNCLASSIFIED" else sector))]
        nstocks=sum(row["Loại"]=="Stock" for row in all_rows)
        capture_date=universe[0].get("capture_date","—") if universe else "—"
        st.caption(f"Phạm vi SSI đã capture ngày {capture_date}: {nstocks:,} cổ phiếu · chỉ hiển thị mã thuộc phiên thu này. Dữ liệu REST độc lập với chế độ mô phỏng {ss['mode']}.")
        top=st.columns(4)
        top[0].metric("Mã trong phiên capture",f"{nstocks:,}")
        top[1].metric("Mã có dữ liệu giao dịch",f"{sum(row['Mã'] in latest for row in all_rows):,}")
        top[2].metric("Mã đã thu quote L3",len(counts["quotes"]))
        top[3].metric("Mã có lịch sử daily / 1m",f"{len(counts['daily'])} / {len(counts['minute'])}")
        query=st.text_input("Tìm trong toàn thị trường",key="market_search",placeholder="Mã, tên doanh nghiệp hoặc ngành: HPG, thực phẩm, thép…").strip().casefold()
        if query:filtered=[r for r in filtered if query in " ".join([r["Mã"],r["Tên doanh nghiệp"],r["Ngành"]]).casefold()]
        hide_empty=st.toggle("Ẩn mã chưa có dữ liệu giao dịch",value=False,key="market_hide_empty")
        if hide_empty:filtered=[row for row in filtered if row["Mã"] in latest]
        st.caption(f"Hiển thị {len(filtered):,} mã · ô trống nghĩa là SSI chưa trả dữ liệu cho phạm vi đã thu · click một dòng để chọn mã.")
        def choose_row():
            event=ss.get("market_table",{})
            selection=event.get("selection",{})
            positions=selection.get("rows",[])
            if positions and positions[0]<len(filtered):state.select_symbol(ss,filtered[positions[0]]["Mã"])
        st.dataframe(filtered,key="market_table",on_select=choose_row,selection_mode="single-row",height=430,hide_index=True,width="stretch",column_order=["Mã","Sàn","Rổ chỉ số","Giá đóng cửa SSI","Thay đổi %","KL khớp SSI","GTGD SSI","Ngành","Tên doanh nghiệp","Ngày giao dịch","Dữ liệu","Quote L3 đã thu","Nến daily","Nến 1m","Loại","Giá tham chiếu SSI"],column_config={
            "Tên doanh nghiệp":st.column_config.TextColumn(width="large"),
            "Giá đóng cửa SSI":st.column_config.NumberColumn(format="localized"),
            "Thay đổi %":st.column_config.NumberColumn(format="%.2f %%"),
            "KL khớp SSI":st.column_config.NumberColumn(format="localized"),
            "GTGD SSI":st.column_config.NumberColumn(format="localized"),
        })
        col1,col2=st.columns(2)
        col1.button("↻ Cập nhật bảng từ kho đã thu",key="refresh_market",on_click=lambda:None)
        buffer=io.StringIO()
        if filtered:
            export=csv.DictWriter(buffer,fieldnames=list(filtered[0]));export.writeheader();export.writerows(filtered)
        col2.download_button("↓ Xuất danh mục đang lọc CSV",buffer.getvalue(),file_name="SSI_HISTORICAL_REST_market.csv",mime="text/csv")
        with st.expander("Quản lý danh sách yêu thích"):
            st.multiselect("Watchlist theo dõi",list(dict.fromkeys(r["symbol"] for r in universe)),key="watchlist",max_selections=50)
            st.caption("Yêu thích chỉ phục vụ giao diện; collector streaming chạy độc lập theo SSI_COLLECTION_SCOPE (WATCHLIST/VN30/ALL).")
    render_selected(st,ss)
    with st.container(key="lg_card_pulse_book"):
        observable=is_observable_book(vm["quote"])
        if observable:
            quote=vm["quote"]
            st.subheader("Sổ lệnh đã lưu · "+ss["selected_symbol"])
            if not vm["trust"]["allowed"]:
                st.warning("Snapshot chỉ dùng để quan sát; mô phỏng LIVE đang khóa: " + " · ".join(vm["trust"]["reasons"]))
            st.dataframe([{"Mức":i,"Bid CP":quote[f"bid_qty_{i}"],"Bid VND/CP":quote[f"bid_price_{i}"],"Ask VND/CP":quote[f"ask_price_{i}"],"Ask CP":quote[f"ask_qty_{i}"]} for i in range(1,4)],hide_index=True,width="stretch")
        else:
            st.warning("Không có snapshot đã xác minh đơn vị/book để quan sát: " + " · ".join(vm["trust"]["reasons"]))
    cols=st.columns(2)
    with cols[0]: chart_card(st,"Bid / Ask Balance · Quan sát","balance",charts.levels(vm["quote"],balance=True) if observable else None)
    with cols[1]: chart_card(st,"Depth by Level · Quan sát","levels",charts.levels(vm["quote"]) if observable else None)
    with st.container(key="lg_card_ohlc"):
        st.subheader("Thanh khoản giao dịch lịch sử · OHLCV")
        st.caption("Giá / khối lượng / giá trị giao dịch đã khớp; lưu trữ riêng với quote L3.")
        if st.toggle("Mở phân tích lịch sử",key="show_ohlc"):
            from data.ohlc_history import load_bars, summarize, intraday_liquidity_windows
            path=ROOT/"data/processed/ohlc_history.jsonl"
            @st.cache_data(show_spinner=False)
            def historical(symbol,mtime):
                return load_bars(path,symbol=symbol)
            bars=historical(ss["selected_symbol"],path.stat().st_mtime if path.exists() else 0)
            daily=[r for r in bars if r.get("timeframe")=="1d"]
            minute=[r for r in bars if r.get("timeframe")=="1m"]
            if daily:
                import plotly.graph_objects as go
                data=summarize(daily)
                st.dataframe(data,hide_index=True,width="stretch")
                fig=go.Figure(go.Scatter(x=[r["trading_date"] for r in daily],y=[r["close"] for r in daily],line_color=charts.PURPLE))
                st.plotly_chart(charts.style(fig,260),width="stretch",key="ohlc_close")
            if minute:
                st.dataframe(intraday_liquidity_windows(minute),hide_index=True,width="stretch")
            if not bars: st.info("Chưa lưu OHLCV cho mã được chọn.")


def replay(st,ss,vm,rows,status):
    with st.container(key="lg_card_replay"):
        st.subheader("Replay · chọn đúng snapshot đã lưu")
        if ss["mode"]!="REPLAY":
            st.info("Chuyển sang REPLAY để phát lại dữ liệu SSI thật đã lưu.")
            st.button("Mở dữ liệu SSI đã lưu",key="enter_replay",on_click=state.change_mode,args=(ss,"REPLAY"))
            if ss["mode"]=="SYNTHETIC_TEST": st.caption("Các snapshot đang xem là fixture SYNTHETIC_TEST.")
        if not rows:
            empty(st,"Chưa có dữ liệu replay cho mã này");return
        st.caption(f"{len(rows)} snapshot · {ss['selected_symbol']} · {ss['mode']} · mốc thời gian UTC+7")
        cols=st.columns([1,1,2])
        cols[0].button("Ⅱ Pause" if ss["playing"] else "▷ Play",key="replay_play",on_click=lambda:ss.update(playing=not ss["playing"]))
        cols[1].button("↶ Đầu cửa sổ",key="replay_reset",on_click=lambda:ss.update(snapshot_id=rows[0]["quote_id"]))
        cols[2].select_slider("Tốc độ · snapshot/giây",[1,2,5,10],key="replay_speed")
        st.write("Snapshot đang chọn:",vm["snapshot_id"])
        st.caption(local_time((vm["quote"] or {}).get("quote_time_vn"))+" UTC+7")
        st.button("Dùng snapshot này trong Simulator",key="replay_to_sim",on_click=state.navigate,args=(ss,"Simulator"))
    compare(st,ss,rows,status,prefix="replay")


def compare(st,ss,rows,status,prefix="charts"):
    with st.container(key=f"lg_card_compare_{prefix}"):
        st.subheader("So sánh hai snapshot")
        if len(rows)<2:
            st.info("Cần ít nhất hai snapshot đã lưu của mã được chọn.");return
        ids=[r["quote_id"] for r in rows]
        labels={r["quote_id"]:local_time(r.get("quote_time_vn"))+" · "+r["quote_id"][:8] for r in rows}
        col1,col2=st.columns(2)
        a=col1.selectbox("Snapshot A",ids,index=0,format_func=labels.get,key=f"compare_a_{prefix}")
        b=col2.selectbox("Snapshot B",ids,index=len(ids)-1,format_func=labels.get,key=f"compare_b_{prefix}")
        qa=next(r for r in rows if r["quote_id"]==a);qb=next(r for r in rows if r["quote_id"]==b)
        va=make_view(qa,ss["mode"],status,ss["trade_side"],ss["requested_qty"]);vb=make_view(qb,ss["mode"],status,ss["trade_side"],ss["requested_qty"])
        if not va["trust"]["allowed"] or not vb["trust"]["allowed"]:
            st.warning("Snapshot A/B chưa vượt Data Trust; chỉ so sánh metadata.")
        st.dataframe([{"Snapshot":x["snapshot_id"],"Thời điểm":local_time(x["quote"].get("quote_time_vn")),"Mode":x["mode"],"Trust":x["trust"]["label"],"Spread bps":fmt(x["metrics"].get("spread_bps"),2),"Bid CP":fmt(x["metrics"].get("bid_depth_3")),"Ask CP":fmt(x["metrics"].get("ask_depth_3"))} for x in [va,vb]],hide_index=True,width="stretch")
        if va["trust"]["allowed"] and vb["trust"]["allowed"]:
            ca,cb=st.columns(2)
            with ca: chart_card(st,"Snapshot A · Depth",f"compare_a_{prefix}",charts.depth(qa))
            with cb: chart_card(st,"Snapshot B · Depth",f"compare_b_{prefix}",charts.depth(qb))


def chart_studio(st,ss,vm,rows,status):
    with st.container(key="lg_card_chart_head"):
        st.subheader("Chart Studio")
        st.caption(f"{ss['selected_symbol']} · {ss['mode']} · L1–L3 · snapshot {vm['snapshot_id'] or '—'}")
    if ss["compare_open"]: compare(st,ss,rows,status)
    q,s=vm["quote"],vm["simulation"]; ok=vm["trust"]["allowed"]
    observable=is_observable_book(q);points=observation_history_points(rows)
    specs=[
        ("Depth Mirror · Quan sát",lambda:charts.depth(q),observable),
        ("Cumulative Depth · Quan sát",lambda:charts.levels(q,True),observable),
        ("Bid / Ask Balance · Quan sát",lambda:charts.levels(q,balance=True),observable),
        ("Sweep Allocation · Mô phỏng",lambda:charts.sweep(s),ok),
        ("Coverage Curve · Mô phỏng",lambda:charts.curve(q,ss["trade_side"],ss["requested_qty"]),ok),
        ("VWAP Price Impact · Mô phỏng",lambda:charts.curve(q,ss["trade_side"],ss["requested_qty"],True),ok),
        ("Spread Timeline · Quan sát",lambda:charts.timeline(points,"spread_bps"),bool(points)),
        ("OBI Timeline · Quan sát",lambda:charts.timeline(points,"obi_3",bar=True),bool(points)),
        ("Bid / Ask Depth Timeline · Quan sát",lambda:charts.timeline(points,"bid_depth_3",second="ask_depth_3"),bool(points)),
    ]
    for index in range(0,len(specs),3):
        for col,(title,fn,available) in zip(st.columns(3),specs[index:index+3]):
            with col: chart_card(st,title,f"studio_{title}",fn() if available else None)
    with st.container(key="lg_card_chart_export"):
        st.button("So sánh snapshot A / B",key="studio_compare",on_click=lambda:ss.update(compare_open=True))
        if ok:
            export=[{"mode":ss["mode"],"symbol":ss["selected_symbol"],"snapshot_id":p["snapshot_id"],"time":p["time"].isoformat(),"spread_bps":str(p["spread_bps"]),"obi":str(p["obi_3"])} for p in points]
            st.download_button("↓ Xuất chuỗi chỉ số JSON",json.dumps(export,ensure_ascii=False),file_name=f"{ss['mode']}_metrics.json",mime="application/json")


def compare_symbols(st, ss, status, universe):
    """Compare executable liquidity across real SSI snapshots only."""
    import math
    import plotly.graph_objects as go

    available = list(dict.fromkeys(row["symbol"] for row in universe))
    metadata = {row["symbol"]: row for row in universe}
    defaults = [symbol for symbol in ss.get("compare_symbols", []) if symbol in available]
    if len(defaults) < 2:
        defaults = [symbol for symbol in ["FPT", "VPB", "SSI", "HPG", "VNM"] if symbol in available][:5]

    st.markdown(
        '''<section class="lg-compare-hero"><div><small>SSI · LIQUIDITY COMPARISON</small>
        <h1>So sánh thanh khoản giữa các mã</h1>
        <p>Đối chiếu khả năng thực thi trên cùng chế độ dữ liệu, ngày giao dịch và khối lượng giả định.</p>
        <span>Spread</span><span>Depth L1–L3</span><span>Coverage</span><span>VWAP impact</span></div></section>''',
        unsafe_allow_html=True,
    )
    with st.container(key="lg_card_compare_picker"):
        selected = st.multiselect(
            "Chọn từ 2 đến 10 mã", available, default=defaults, max_selections=10,
            key="compare_symbol_picker", help="Chỉ dùng các mã thuộc phạm vi SSI đã capture.",
        )
        ss["compare_symbols"] = selected
        st.caption(f"{ss['mode']} · ngày {ss.get('selected_date') or 'mới nhất'} · khối lượng giả định {fmt(ss['requested_qty'])} CP · tối đa 10 mã")
    if len(selected) < 2:
        st.info("Hãy chọn ít nhất hai mã để so sánh.")
        return

    records = []
    histories = {}
    for symbol in selected:
        symbol_rows = load_quotes(ss["mode"], symbol)
        if ss["mode"] == "REPLAY" and ss.get("selected_date"):
            symbol_rows = [
                row for row in symbol_rows
                if (lambda stamp: stamp is not None and stamp.date().isoformat() == ss["selected_date"])(
                    parse_time(row.get("quote_time_vn") or row.get("received_at_utc"))
                )
            ]
        histories[symbol] = observation_history_points(symbol_rows)
        candidates = []
        for quote in symbol_rows:
            view = make_view(quote, ss["mode"], status, ss["trade_side"], ss["requested_qty"], stale_seconds=ss["stale_seconds"])
            if view["trust"]["allowed"]:
                candidates.append(view)
        if not candidates:
            records.append({
                "symbol": symbol, "board": metadata.get(symbol, {}).get("board", "—"),
                "sector": metadata.get(symbol, {}).get("sector", "UNCLASSIFIED"),
                "trust": "BLOCKED", "reason": "Không có snapshot đủ Data Trust trong phạm vi đã chọn",
            })
            continue
        view = candidates[-1]
        metric, simulation, quote = view["metrics"], view["simulation"], view["quote"]
        records.append({
            "symbol": symbol, "board": metadata.get(symbol, {}).get("board", "—"),
            "sector": metadata.get(symbol, {}).get("sector", "UNCLASSIFIED"),
            "trust": view["trust"]["label"], "reason": "",
            "time": local_time(quote.get("quote_time_vn"), True),
            "spread": metric.get("spread_bps"), "bid_depth": metric.get("bid_depth_3"),
            "ask_depth": metric.get("ask_depth_3"),
            "depth": (metric.get("bid_depth_3") or 0) + (metric.get("ask_depth_3") or 0),
            "obi": metric.get("obi_3"), "coverage": simulation.get("coverage_ratio") * 100 if simulation else None,
            "impact": abs(simulation.get("slippage_bps")) if simulation and simulation.get("slippage_bps") is not None else None,
        })

    valid = [row for row in records if row.get("coverage") is not None]
    def normalized(value, values, inverse=False):
        finite = [float(number) for number in values if number is not None and math.isfinite(float(number))]
        if value is None or not finite:
            return 0.0
        low, high = min(finite), max(finite)
        score = 1.0 if high == low else (float(value) - low) / (high - low)
        return 1.0 - score if inverse else score

    for row in valid:
        row["score"] = 100 * (
            .25 * normalized(row["spread"], [item["spread"] for item in valid], True)
            + .25 * normalized(row["depth"], [item["depth"] for item in valid])
            + .30 * normalized(row["coverage"], [item["coverage"] for item in valid])
            + .20 * normalized(row["impact"], [item["impact"] for item in valid], True)
        )
    valid.sort(key=lambda row: row["score"], reverse=True)
    rank = {row["symbol"]: index + 1 for index, row in enumerate(valid)}

    with st.container(key="lg_card_compare_summary"):
        if valid:
            best = valid[0]
            cols = st.columns(5)
            cols[0].metric("Mã đứng đầu", best["symbol"])
            cols[1].metric("Điểm thanh khoản", f"{best['score']:.1f}/100")
            cols[2].metric("Spread", f"{best['spread']:.2f} bps")
            cols[3].metric("Depth 3 mức", fmt(best["depth"]) + " CP")
            cols[4].metric("Coverage", f"{best['coverage']:.1f}%")
        else:
            st.warning("Không có mã nào đủ Data Trust để tính so sánh trong phạm vi đã chọn.")

    table = []
    for row in records:
        table.append({
            "Hạng": rank.get(row["symbol"], "—"), "Mã": row["symbol"], "Sàn": row["board"],
            "Ngành": "Chưa phân loại" if row["sector"] == "UNCLASSIFIED" else row["sector"],
            "Điểm": round(row.get("score", 0), 1) if row.get("score") is not None else None,
            "Spread (bps)": row.get("spread"), "Depth 3 mức (CP)": row.get("depth"),
            "Coverage (%)": row.get("coverage"), "Impact (bps)": row.get("impact"),
            "OBI": row.get("obi"), "Snapshot": row.get("time", "—"), "Data Trust": row["trust"],
        })
    with st.container(key="lg_card_compare_table"):
        st.subheader("Bảng xếp hạng khả năng thực thi")
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption("Điểm chỉ so sánh khả năng thực thi trong nhóm mã đang chọn: Spread 25%, Depth 25%, Coverage 30%, Impact 20%. Không phải khuyến nghị đầu tư.")

    if valid:
        symbols = [row["symbol"] for row in valid]
        cols = st.columns(3, gap="small")
        spread = go.Figure(go.Bar(x=symbols, y=[row["spread"] for row in valid], marker_color="#9563C4"))
        depth = go.Figure()
        depth.add_bar(name="Bid", x=symbols, y=[row["bid_depth"] for row in valid], marker_color="#A8DDB5")
        depth.add_bar(name="Ask", x=symbols, y=[row["ask_depth"] for row in valid], marker_color="#F2A0B6")
        execution = go.Figure(go.Scatter(
            x=[row["coverage"] for row in valid], y=[row["impact"] for row in valid], mode="markers+text",
            text=symbols, textposition="top center", marker={"size": 16, "color": [row["score"] for row in valid], "colorscale": "Purples"},
        ))
        execution.update_xaxes(title="Coverage (%)"); execution.update_yaxes(title="Impact (bps)")
        with cols[0]: chart_card(st, "Spread theo mã", "compare_symbol_spread", charts.style(spread, 260))
        with cols[1]: chart_card(st, "Bid/Ask Depth ba mức", "compare_symbol_depth", charts.style(depth, 260))
        with cols[2]: chart_card(st, "Coverage và Price Impact", "compare_symbol_execution", charts.style(execution, 260))

        timeline = go.Figure()
        for symbol in symbols[:5]:
            points = histories.get(symbol, [])
            timeline.add_scatter(x=[point["time"] for point in points], y=[point.get("spread_bps") for point in points], mode="lines", name=symbol)
        with st.container(key="lg_card_compare_timeline"):
            st.subheader("Diễn biến Spread của tối đa 5 mã")
            st.plotly_chart(charts.style(timeline, 290), width="stretch", config={"displayModeBar": False})


def alerts(st,ss,vm,rows,status):
    with st.container(key="lg_card_alerts"):
        st.subheader("Alerts & Data Trust")
        st.caption("Trạng thái hiện tại: "+vm["trust"]["label"])
        for reason in vm["trust"]["reasons"]:
            st.warning(reason)
        if not vm["trust"]["reasons"]:
            st.success("Các điều kiện kiểm tra hiện có đều đạt" + (" trên fixture SYNTHETIC_TEST." if ss["mode"]=="SYNTHETIC_TEST" else "."))
        q=vm["quote"] or {}
        fields={"Provider":q.get("provider"),"Source":q.get("source"),"Mode":ss["mode"],"Snapshot ID":vm["snapshot_id"],"Raw event ID":q.get("raw_event_id"),"Quote timestamp UTC+7":local_time(q.get("quote_time_vn")),"Quote age · giây":fmt(vm["trust"]["age_seconds"]),"Đơn vị giá":q.get("price_unit"),"Đơn vị khối lượng":q.get("quantity_unit"),"Bằng chứng đơn vị":q.get("unit_evidence_ref"),"Market phase":q.get("market_phase") or "UNKNOWN","Phase source":q.get("market_phase_source") or "UNKNOWN","Book integrity":q.get("is_valid_book"),"Snapshot hoàn chỉnh verified":q.get("complete_book_verified"),"Collector":status.get("state"),"Cập nhật WS UTC+7":local_time(status.get("updated_at_utc"))}
        st.dataframe([{"Điều kiện":k,"Giá trị":str(v) if v is not None else "UNKNOWN"} for k,v in fields.items()],hide_index=True,width="stretch")
        cols=st.columns(2)
        cols[0].button("Mở mô phỏng snapshot liên quan",key="alert_simulator",on_click=state.navigate,args=(ss,"Simulator"))
        cols[1].button("Xem lịch sử liên quan",key="alert_replay",on_click=state.navigate,args=(ss,"Replay"))
        if q.get("quality_flags"): st.caption("Quality flags: "+", ".join(q["quality_flags"]))
        qa=ROOT/"outputs/qa/data_quality.json"
        if qa.exists():
            report=json.loads(qa.read_text())
            st.caption(f"Kho hiện có {report.get('quote_count',0)} quotes; {report.get('full_session_days_observed',0)} ngày đủ toàn phiên. Các ngày chỉ thu cửa sổ ngắn chưa đủ bằng chứng cả phiên.")


def settings(st,ss,status):
    with st.container(key="lg_settings"):
        st.subheader("Settings · Workspace")
        cols=st.columns(2)
        cols[0].selectbox("Mật độ giao diện",["Thoải mái","Gọn"],key="density")
        cols[1].selectbox("Định dạng số",["1.234,56","1,234.56"],key="number_format")
        st.number_input("Ngưỡng STALE cho LIVE · giây",min_value=5,max_value=300,step=5,key="stale_seconds")
        st.caption("Timezone: Asia/Ho_Chi_Minh (UTC+7) · Provider: SSI FastConnect · Quyền: Market Data read-only")
        st.subheader("Giao diện · Design tokens")
        for name,color in [("Deep Plum","#3E2F4F"),("Dusty Lavender","#BDAFD1"),("Soft Lilac","#DCCFF0"),("Warm Sand","#D7B38C"),("Cream Beige","#F2E6D7"),("Blush Pink","#F3C9DD")]:
            st.markdown(f'<span class="lg-pill" style="background:{color};color:{"white" if name=="Deep Plum" else "#30243C"}">{name} · {color}</span>',unsafe_allow_html=True)
        preferences={key:ss[key] for key in ["density","number_format","watchlist","stale_seconds"]}
        st.download_button("↓ Lưu bố cục và tùy chọn",json.dumps(preferences,ensure_ascii=False,indent=2),file_name="liquidityguard_preferences.json",mime="application/json")
        uploaded=st.file_uploader("Khôi phục tùy chọn đã lưu",type=["json"])
        if uploaded and st.button("Áp dụng tùy chọn",key="restore_preferences"):
            try:
                data=json.loads(uploaded.getvalue())
                if data.get("density") not in ["Thoải mái","Gọn"] or data.get("number_format") not in ["1.234,56","1,234.56"]: raise ValueError()
                ss["pending_preferences"]={k:v for k,v in data.items() if k in preferences};st.rerun()
            except (ValueError,TypeError): st.error("File tùy chọn không hợp lệ.")
        st.caption("Tùy chọn không chứa API key, token hoặc mật khẩu. Kết nối collector được cấu hình riêng trong môi trường cục bộ.")
