"""Plotly charts over validated backend results; no financial calculations here."""
from __future__ import annotations
from datetime import timedelta
import plotly.graph_objects as go
from app.view_models import coverage_points

PURPLE, SAND, MINT, CORAL = "#9563C4", "#D7B38C", "#A8DDB5", "#F2A0B6"


def style(fig, height=165):
    fig.update_layout(height=height, margin=dict(l=12, r=12, t=12, b=28),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=11, color="#30243C"),
        legend=dict(orientation="h", y=-.24, x=.5, xanchor="center", font_size=10),
        hoverlabel=dict(bgcolor="#FAF7FC", font_color="#30243C"),
        colorway=[PURPLE, SAND, MINT, CORAL], showlegend=False)
    fig.update_xaxes(gridcolor="rgba(62,47,79,.07)", zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor="rgba(62,47,79,.09)", zerolinecolor="#BDAFD1", automargin=True)
    return fig


def depth(quote):
    fig = go.Figure()
    for side, label, color in [("bid", "Bid", PURPLE), ("ask", "Ask", SAND)]:
        points = []
        for i in range(1, 4):
            price, qty = quote.get(f"{side}_price_{i}"), quote.get(f"{side}_qty_{i}")
            # SSI [0,0] means an empty level, not a zero-price order.
            if price in (None, "", 0, "0") and int(qty or 0) == 0:
                continue
            points.append((float(price), int(qty), i))
        total = 0; cumulative = []
        for price, qty, level in points:
            total += qty; cumulative.append((price, total, qty, level))
        cumulative.sort(key=lambda item:item[0])
        fig.add_trace(go.Scatter(x=[p for p, total, qty, level in cumulative], y=[total for p, total, qty, level in cumulative],
            mode="lines+markers", name=label, line=dict(color=color, width=2, shape="hv"), fill="tozeroy",
            customdata=[[level,qty] for p,total,qty,level in cumulative],
            hovertemplate=f"{label} L%{{customdata[0]}}<br>Giá %{{x:,.0f}} VND/CP<br>Tại mức %{{customdata[1]:,.0f}} CP<br>Tích lũy %{{y:,.0f}} CP<extra></extra>"))
    fig.update_layout(showlegend=True)
    fig.update_xaxes(title_text="Giá · VND/CP", title_font_size=10)
    return style(fig)


def sweep(simulation):
    labels, values, prices = [], [], []
    for fill in simulation["level_fills"]:
        if fill["filled_qty"]:
            labels.append(f"L{fill['level']}"); values.append(fill["filled_qty"]); prices.append(float(fill["price"]))
    if simulation["unfilled_qty"]:
        labels.append("Chưa đáp ứng"); values.append(simulation["unfilled_qty"]); prices.append(None)
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=.72, sort=False,
        marker=dict(colors=[PURPLE, "#BDAFD1", SAND, CORAL]), textinfo="none",
        customdata=prices,
        hovertemplate="%{label}<br>%{value:,.0f} CP · %{percent}<br>Giá %{customdata:,.0f} VND/CP<extra></extra>"))
    fig.add_annotation(text=f"<b>{simulation['requested_qty']:,}</b><br>CP giả định", x=.5,y=.5, showarrow=False, font_size=13)
    fig.update_layout(showlegend=True)
    return style(fig)


def curve(quote, side, quantity, impact=False):
    book_side = "ask" if side == "BUY" else "bid"
    maximum = max(quantity, sum(int(quote[f"{book_side}_qty_{i}"]) for i in range(1, 4)))
    points = coverage_points(quote, side, maximum)
    fig = go.Figure(go.Scatter(x=[p["quantity"] for p in points], y=[float(p["impact"] or 0) if impact else p["coverage"] for p in points],
        mode="lines", line=dict(color=PURPLE, width=2.4), fill="tozeroy", fillcolor="rgba(149,99,196,.15)",
        hovertemplate="Yêu cầu %{x:,.0f} CP<br>%{y:.2f}" + (" bps" if impact else "%") + "<extra></extra>"))
    exact = min(points, key=lambda point:abs(point["quantity"]-quantity)) if points else None
    if exact:
        value = float(exact["impact"] or 0) if impact else exact["coverage"]
        fig.add_vline(x=quantity,line_width=1,line_dash="dot",line_color="#3E2F4F")
        fig.add_trace(go.Scatter(x=[quantity],y=[value],mode="markers",marker=dict(size=8,color=CORAL),
            hovertemplate="Q đang chọn %{x:,.0f} CP<br>%{y:.2f}" + (" bps" if impact else "%") + "<extra></extra>"))
    fig.update_xaxes(title_text="Khối lượng yêu cầu · CP", title_font_size=10)
    fig.update_yaxes(range=None if impact else [0, 105], ticksuffix=" bps" if impact else "%")
    return style(fig)


def timeline(points, field, *, bar=False, second=None):
    fig = go.Figure()
    # Insert explicit nulls at missing windows so Plotly never bridges lunch or downtime.
    x, y, y2 = [], [], []
    previous = None
    for point in points:
        dt = point["time"]
        if dt is None:
            continue
        if previous and (dt - previous).total_seconds() > 60:
            x.append(previous + timedelta(seconds=1)); y.append(None); y2.append(None)
        x.append(dt); y.append(float(point[field]) if point.get(field) is not None else None)
        y2.append(float(point[second]) if second and point.get(second) is not None else None)
        previous = dt
    if bar:
        custom=[]
        point_by_time={point["time"]:point for point in points if point.get("time")}
        for stamp in x:
            point=point_by_time.get(stamp,{})
            custom.append([point.get("bid_depth_3"),point.get("ask_depth_3")])
        fig.add_trace(go.Bar(x=x, y=y, customdata=custom,
            marker_color=[MINT if v is not None and v >= 0 else CORAL for v in y], name="OBI",
            hovertemplate="%{x|%d/%m %H:%M:%S}<br>BidDepth %{customdata[0]:,.0f} CP<br>AskDepth %{customdata[1]:,.0f} CP<br>OBI %{y:.3f}<extra></extra>"))
        fig.update_yaxes(range=[-1,1],title_text="OBI")
    else:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", connectgaps=False, marker_size=3, line=dict(color=PURPLE,width=2), name=field,
            hovertemplate="%{x|%d/%m %H:%M:%S}<br>Spread %{y:.2f} bps<extra></extra>"))
        if field=="spread_bps": fig.update_yaxes(title_text="Spread · bps")
    if second:
        fig.add_trace(go.Scatter(x=x, y=y2, connectgaps=False, line=dict(color=SAND,width=2),name=second))
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%d/%m %H:%M:%S")
    return style(fig, 150)


def levels(quote, cumulative=False, balance=False):
    fig = go.Figure()
    for side, color in [("bid", MINT), ("ask", CORAL)]:
        values = [int(quote[f"{side}_qty_{i}"]) for i in range(1,4)]
        if cumulative:
            values = [sum(values[:i]) for i in range(1,4)]
        fig.add_trace(go.Bar(x=["L1", "L2", "L3"],y=values, name=side.upper(),marker_color=color))
    fig.update_layout(barmode="group",showlegend=True)
    if balance:
        bid = sum(int(quote[f"bid_qty_{i}"]) for i in range(1,4)); ask = sum(int(quote[f"ask_qty_{i}"]) for i in range(1,4))
        fig = go.Figure(go.Pie(labels=["Bid", "Ask"],values=[bid,ask], hole=.65,marker_colors=[MINT,CORAL]))
    return style(fig, 245)
