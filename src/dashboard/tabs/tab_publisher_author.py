from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ..format_utils import apply_chart_style, format_vn
from ..ui_cards import render_metric_strip

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub


def _clean_author(x):
    if pd.isna(x):
        return "Ẩn danh"
    s = str(x).strip()
    if s in ["", ".", ",", "-", "Unknown"]:
        return "Ẩn danh"
    if s.lower() in ["nhiều tác giả", "nhiều tac gia"]:
        return "Nhiều tác giả"
    return s



def _render_kpi_row(items):
    render_metric_strip(
        [{"label": l, "value": v, "icon": i, "tone": t} for l, v, i, t in items],
        compact=True,
    )


def _fmt_k(n):
    if pd.isna(n): return ""
    if n >= 1e6: return f"{format_vn(n/1e6,1)}M"
    if n >= 1e3: return f"{format_vn(n/1e3,1)}K"
    return format_vn(n)



# ---------------------------------------------------------------------------
# CHART 1 — Top 15 NXB doanh số TB  (H-Bar)
# ---------------------------------------------------------------------------

def _chart_top_publishers(df, colors):
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns:
        st.info("Không có cột publisher_vn."); return
    pub = (sold_df.groupby("publisher_vn")
           .agg(avg_sold=("all_time_quantity_sold","mean"), n=("all_time_quantity_sold","size"))
           .reset_index())
    pub = pub[pub["n"]>=0].sort_values("avg_sold",ascending=True).tail(15)
    
    # Truncate long publisher names for better display
    pub["publisher_short"] = pub["publisher_vn"].apply(lambda x: str(x)[:30] + "..." if len(str(x)) > 30 else str(x))
    
    fig = px.bar(pub, x="avg_sold", y="publisher_short", orientation="h",
                 color="avg_sold", color_continuous_scale=[[0,colors[0]],[1,colors[1]]],
                 labels={"avg_sold":"Lượng bán TB","publisher_short":"NXB"},
                 title="Top 15 NXB — Doanh số trung bình (≥5 đầu sách)",
                 text=pub["avg_sold"].apply(lambda x: format_vn(x)),
                 hover_data={"publisher_vn": True, "publisher_short": False})
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", yaxis_categoryorder="total ascending",
                      margin=dict(t=50,b=10,l=10,r=10), height=350)
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# CHART 2 — Donut thị phần NXB  (Donut)
# ---------------------------------------------------------------------------

def _chart_publisher_donut(df, colors):
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns:
        st.info("Thiếu cột publisher_vn."); return
    pub = sold_df.groupby("publisher_vn")["all_time_quantity_sold"].sum().reset_index()
    pub = pub.sort_values("all_time_quantity_sold", ascending=False)
    top = pub.head(10).copy()
    other_val = pub.iloc[10:]["all_time_quantity_sold"].sum() if len(pub) > 10 else 0
    if other_val > 0:
        top = pd.concat([top, pd.DataFrame([{"publisher_vn":"Khác","all_time_quantity_sold":other_val}])],
                        ignore_index=True)
                        
    top["publisher_short"] = top["publisher_vn"].apply(lambda x: str(x)[:25] + "..." if len(str(x)) > 25 else str(x))
    
    fig = go.Figure(go.Pie(
        labels=top["publisher_short"], values=top["all_time_quantity_sold"],
        hole=0.52, textinfo="percent", textposition="inside",
        customdata=top["publisher_vn"],
        marker=dict(colors=px.colors.qualitative.Set2[:len(top)]),
        hovertemplate="<b>%{customdata}</b><br>Tổng bán: %{value:,.0f}<br>Tỷ trọng: %{percent}<extra></extra>"))
    fig.update_layout(title="Thị phần theo NXB (Top 10 + Khác)",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=True, legend=dict(font_size=10, orientation="h", y=-0.2),
                      margin=dict(t=50,b=10,l=10,r=10), height=350)
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# CHART 3 — Pareto tác giả (Doanh thu)  (Bar + Line combo)
# ---------------------------------------------------------------------------

def _chart_author_pareto(df, colors):
    sold_df = _filter_sold(df)
    if "authors" not in sold_df.columns or "price" not in sold_df.columns:
        st.info("Thiếu cột authors hoặc price."); return
        
    sold_df["authors"] = sold_df["authors"].apply(_clean_author)
    price = pd.to_numeric(sold_df["price"], errors="coerce").fillna(0)
    sold_df["revenue"] = sold_df["all_time_quantity_sold"] * price
    
    agg = (sold_df.groupby("authors")["revenue"].sum()
           .reset_index().sort_values("revenue", ascending=False).head(20)) # Giảm xuống top 20 để đỡ rối
    agg["cum_pct"] = agg["revenue"].cumsum() / agg["revenue"].sum() * 100
    
    # Cắt ngắn tên tác giả nếu quá dài
    agg["author_short"] = agg["authors"].apply(lambda x: str(x)[:20] + "..." if len(str(x)) > 20 else str(x))

    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg["author_short"], y=agg["revenue"],
                         name="Tổng doanh thu", marker_color=colors[0], opacity=0.85, yaxis="y1",
                         customdata=agg["authors"],
                         hovertemplate="<b>%{customdata}</b><br>Doanh thu: %{y:,.0f} ₫<extra></extra>"))
    fig.add_trace(go.Scatter(x=agg["author_short"], y=agg["cum_pct"], name="% tích lũy",
                             mode="lines+markers", line=dict(color=colors[1],width=2),
                             marker=dict(size=6), yaxis="y2",
                             hovertemplate="%{y:.1f}%<extra></extra>"))
    fig.add_hline(y=80, line_dash="dot", line_color="#1E40AF",
                  annotation_text="80%", annotation_position="right", yref="y2")
    fig.update_layout(
        title="Pareto: Top 20 tác giả & % Doanh thu tích lũy",
        xaxis_tickangle=-45,
        yaxis=dict(title="Tổng doanh thu (₫)"),
        yaxis2=dict(title="% tích lũy", overlaying="y", side="right", range=[0,105]),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=80,b=120,l=10,r=40), height=450)
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# CHART 4 — Tác giả: Ổn định vs Siêu phẩm  (Scatter)
# ---------------------------------------------------------------------------

def _chart_author_consistency(df, colors):
    sold_df = _filter_sold(df)
    if "authors" not in sold_df.columns or "price" not in sold_df.columns:
        st.info("Thiếu cột authors hoặc price."); return
        
    sold_df["authors"] = sold_df["authors"].apply(_clean_author)
    price = pd.to_numeric(sold_df["price"], errors="coerce").fillna(0)
    sold_df["revenue"] = sold_df["all_time_quantity_sold"] * price
    
    agg = (sold_df.groupby("authors")
           .agg(n=("revenue","size"),
                avg_rev=("revenue","mean"),
                max_rev=("revenue","max"),
                total=("revenue","sum"))
           .reset_index())
    agg = agg[agg["n"]>=3].copy()
    agg["max_share"] = agg["max_rev"] / agg["total"] * 100  # % doanh thu mà cuốn thành công nhất chiếm

    fig = px.scatter(agg, x="avg_rev", y="max_share", size="total",
                     hover_name="authors", size_max=35, opacity=0.65,
                     color="n", color_continuous_scale=[[0,"#fbbf24"],[0.5,"#f97316"],[1,"#dc2626"]],
                     labels={"avg_rev":"Doanh thu TB/cuốn","max_share":"% siêu phẩm chiếm",
                             "n":"Số đầu sách","total":"Lượng GD"},
                     title="Tác giả: Ổn định đều tay vs Phụ thuộc siêu phẩm")
    fig.add_hline(y=50, line_dash="dot", line_color="#94a3b8",
                  annotation_text="50%", annotation_position="top left")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=80,b=20,l=10,r=10), height=450)
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)

def render_publisher_author_tab(
    df: pd.DataFrame, *, colors: list[str], heatmap_scale: str,
) -> None:
    # --- KPI ---
    sold_df = _filter_sold(df)
    n_pub = int(df["publisher_vn"].nunique()) if "publisher_vn" in df.columns else 0
    n_auth = int(df["authors"].nunique()) if "authors" in df.columns else 0
    avg_sold = float(sold_df["all_time_quantity_sold"].mean())
    price_col = pd.to_numeric(sold_df.get("price", pd.Series(dtype=float)), errors="coerce").fillna(0)
    est_rev = float((price_col * sold_df["all_time_quantity_sold"]).sum())
    _render_kpi_row([
        ("Số NXB", format_vn(n_pub), "building", "blue"),
        ("Số tác giả", format_vn(n_auth), "users", "amber"),
        ("Doanh số TB", format_vn(avg_sold, 0), "chart", "blue"),
        ("Tổng GT Giao Dịch", f"{_fmt_k(est_rev)} ₫", "money", "slate"),
    ])

    # ── SECTION 1: TÁC GIẢ ──

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_author_pareto(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_author_consistency(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SECTION 2: NHÀ XUẤT BẢN ──

    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_top_publishers(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_d:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_publisher_donut(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)

