from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ..format_utils import format_vn
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


def _apply_black_text(fig) -> None:
    fig.update_layout(font={"color": "#000"}, title={"font": {"color": "#000"}})
    fig.update_xaxes(title_font_color="#000", tickfont_color="#000",
                     showgrid=True, gridcolor="#e7edf5", zerolinecolor="#dbe7f2", linecolor="#dbe7f2")
    fig.update_yaxes(title_font_color="#000", tickfont_color="#000",
                     showgrid=True, gridcolor="#e7edf5", zerolinecolor="#dbe7f2", linecolor="#dbe7f2")


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


def _section(title: str, icon: str = "📊") -> None:
    st.markdown(
        f"<div class='section-row-title'>{icon} {title}</div>",
        unsafe_allow_html=True,
    )

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
    fig = px.bar(pub, x="avg_sold", y="publisher_vn", orientation="h",
                 color="avg_sold", color_continuous_scale=[[0,colors[0]],[1,colors[1]]],
                 labels={"avg_sold":"Lượng bán TB","publisher_vn":"NXB"},
                 title="Top 15 NXB — Doanh số trung bình (≥5 đầu sách)",
                 text=pub["avg_sold"].apply(lambda x: format_vn(x)))
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", yaxis_categoryorder="total ascending",
                      margin=dict(t=50,b=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- Chỉ lấy NXB có **≥5 đầu sách** để tránh bias.\n- NXB dẫn đầu thường có hệ thống phân phối mạnh hoặc tập trung vào thể loại hot.")

# ---------------------------------------------------------------------------
# CHART 2 — Donut thị phần NXB  (Donut)
# ---------------------------------------------------------------------------

def _chart_publisher_donut(df, colors):
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns:
        st.info("Thiếu cột publisher_vn."); return
    pub = sold_df.groupby("publisher_vn")["all_time_quantity_sold"].sum().reset_index()
    pub = pub.sort_values("all_time_quantity_sold", ascending=False)
    top = pub.head(15).copy()
    other_val = pub.iloc[15:]["all_time_quantity_sold"].sum() if len(pub) > 8 else 0
    if other_val > 0:
        top = pd.concat([top, pd.DataFrame([{"publisher_vn":"Khác","all_time_quantity_sold":other_val}])],
                        ignore_index=True)
    fig = go.Figure(go.Pie(
        labels=top["publisher_vn"], values=top["all_time_quantity_sold"],
        hole=0.52, textinfo="label+percent",
        marker=dict(colors=px.colors.qualitative.Set2[:len(top)]),
        hovertemplate="<b>%{label}</b><br>Tổng bán: %{value:,.0f}<br>Tỷ trọng: %{percent}<extra></extra>"))
    fig.update_layout(title="Thị phần doanh số theo NXB (Top 15 + Khác)",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=True, legend=dict(font_size=10),
                      margin=dict(t=50,b=10,l=10,r=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- Nếu 2-3 NXB chiếm >50% → thị trường **tập trung cao**, ít cạnh tranh.\n- Phần \"Khác\" lớn → nhiều NXB nhỏ cùng chia sẻ thị phần.")

# ---------------------------------------------------------------------------
# CHART 3 — NXB Bubble: Quy mô vs Hiệu quả  (Bubble)
# ---------------------------------------------------------------------------

def _chart_publisher_bubble(df, colors):
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns:
        st.info("Thiếu cột publisher_vn."); return
    pub = (sold_df.groupby("publisher_vn")
           .agg(avg_sold=("all_time_quantity_sold","mean"),
                total_sold=("all_time_quantity_sold","sum"),
                n=("all_time_quantity_sold","size"))
           .reset_index())
    pub = pub[pub["n"]>=3].copy()
    fig = px.scatter(pub, x="n", y="avg_sold", size="total_sold",
                     color="avg_sold", color_continuous_scale=[[0,"#a5b4fc"],[0.5,"#3b82f6"],[1,"#1e3a8a"]],
                     hover_name="publisher_vn", size_max=45, opacity=0.7,
                     labels={"n":"Số đầu sách","avg_sold":"Doanh số TB","total_sold":"Tổng bán"},
                     title="NXB: Quy mô danh mục vs Hiệu quả bán hàng")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      coloraxis_colorbar_title="DS TB", margin=dict(t=50,b=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- Bong bóng lớn + nằm cao → NXB **vừa nhiều sách, vừa bán tốt**.\n- NXB nhỏ nằm cao → niche nhưng hiệu quả.\n- NXB lớn nằm thấp → cần xem lại chiến lược.")

# ---------------------------------------------------------------------------
# CHART 4 — Pareto tác giả  (Bar + Line combo)
# ---------------------------------------------------------------------------

def _chart_author_pareto(df, colors):
    sold_df = _filter_sold(df)
    if "authors" not in sold_df.columns:
        st.info("Thiếu cột authors."); return
    sold_df["authors"] = sold_df["authors"].apply(_clean_author)
    agg = (sold_df.groupby("authors")["all_time_quantity_sold"].sum()
           .reset_index().sort_values("all_time_quantity_sold",ascending=False).head(30))
    agg["cum_pct"] = agg["all_time_quantity_sold"].cumsum() / agg["all_time_quantity_sold"].sum() * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg["authors"], y=agg["all_time_quantity_sold"],
                         name="Tổng lượng bán", marker_color=colors[0], opacity=0.85, yaxis="y1"))
    fig.add_trace(go.Scatter(x=agg["authors"], y=agg["cum_pct"], name="% tích lũy",
                             mode="lines+markers", line=dict(color=colors[1],width=2),
                             marker=dict(size=6), yaxis="y2"))
    fig.add_hline(y=80, line_dash="dot", line_color="#1E40AF",
                  annotation_text="80%", annotation_position="right", yref="y2")
    fig.update_layout(
        title="Pareto: Top 30 tác giả & doanh số tích lũy",
        xaxis_tickangle=-45,
        yaxis=dict(title="Tổng lượng bán"),
        yaxis2=dict(title="% tích lũy", overlaying="y", side="right", range=[0,105]),
        legend=dict(orientation="h",y=1.12,x=0.5,xanchor="center"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50,b=80))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- Đường cắt **80%** sớm → thị trường tập trung vào ít tác giả.\n- Tác giả bar cao + nhiều đầu sách → bán đều tay, ổn định.")

# ---------------------------------------------------------------------------
# CHART 5 — Top 15 sách bán chạy  (H-Bar)
# ---------------------------------------------------------------------------

def _chart_top_books(df, colors):
    sold_col = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    valid = df[sold_col > 0].copy()
    valid["quantity"] = pd.to_numeric(valid["all_time_quantity_sold"], errors="coerce")
    title_col = next((c for c in ["name","title","product_name","book_name"] if c in df.columns), None)
    if "authors" not in valid.columns or not title_col:
        st.info("Thiếu cột authors hoặc tên sách."); return
    valid["authors"] = valid["authors"].apply(_clean_author)
    top = valid.sort_values("quantity",ascending=False).head(15).copy()
    top["short"] = top[title_col].astype(str).apply(lambda x: x[:42]+"..." if len(x)>42 else x)
    top["short"] = [f"{t}{chr(8204)*i}" for i,t in enumerate(top["short"])]
    top["txt"] = "✍️ <b>"+top["authors"]+"</b> &nbsp;|&nbsp; "+top["quantity"].apply(lambda x: format_vn(x))

    fig = go.Figure(go.Bar(
        y=top["short"], x=top["quantity"], orientation="h",
        marker_color=colors[0], text=top["txt"], textposition="outside",
        cliponaxis=False, textfont_color="#0f2740",
        customdata=top["authors"],
        hovertemplate="<b>%{y}</b><br>Tác giả: %{customdata}<br>Lượng bán: %{x:,.0f}<extra></extra>"))
    fig.update_layout(title="Top 15 tác phẩm bán chạy nhất",
                      yaxis_categoryorder="total ascending", yaxis_title="",
                      xaxis_title="Lượng bán", plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=40,t=50,b=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- Đối chiếu với Pareto: tác giả top nhờ **siêu phẩm** hay nhờ **bán đều tay** trên nhiều tựa.")

# ---------------------------------------------------------------------------
# CHART 6 — Tác giả: Ổn định vs Siêu phẩm  (Scatter)
# ---------------------------------------------------------------------------

def _chart_author_consistency(df, colors):
    sold_df = _filter_sold(df)
    if "authors" not in sold_df.columns:
        st.info("Thiếu cột authors."); return
    sold_df["authors"] = sold_df["authors"].apply(_clean_author)
    agg = (sold_df.groupby("authors")
           .agg(n=("all_time_quantity_sold","size"),
                avg_sold=("all_time_quantity_sold","mean"),
                max_sold=("all_time_quantity_sold","max"),
                total=("all_time_quantity_sold","sum"))
           .reset_index())
    agg = agg[agg["n"]>=3].copy()
    agg["max_share"] = agg["max_sold"] / agg["total"] * 100  # % do cuốn bán chạy nhất chiếm

    fig = px.scatter(agg, x="avg_sold", y="max_share", size="total",
                     hover_name="authors", size_max=35, opacity=0.65,
                     color="n", color_continuous_scale=[[0,"#fbbf24"],[0.5,"#f97316"],[1,"#dc2626"]],
                     labels={"avg_sold":"Doanh số TB/cuốn","max_share":"% cuốn bán chạy nhất chiếm",
                             "n":"Số đầu sách","total":"Tổng bán"},
                     title="Tác giả: Ổn định đều tay vs Phụ thuộc siêu phẩm")
    fig.add_hline(y=50, line_dash="dot", line_color="#94a3b8",
                  annotation_text="50% — Ngưỡng phụ thuộc", annotation_position="top left")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=50,b=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- **Dưới 50%**: tác giả bán đều tay → ít rủi ro.\n- **Trên 50%**: phụ thuộc 1 cuốn → rủi ro cao nếu cuốn đó hết trend.\n- Bong bóng lớn + thấp = tác giả **ổn định và mạnh**.")

# ---------------------------------------------------------------------------
# CHART 7 — NXB: Rating TB vs Doanh số TB  (Scatter combo)
# ---------------------------------------------------------------------------

def _chart_publisher_rating(df, colors):
    sold_df = _filter_sold(df)
    needed = {"publisher_vn","rating_average"}
    if not needed.issubset(sold_df.columns):
        st.info("Thiếu cột rating_average hoặc publisher_vn."); return
    rating = pd.to_numeric(sold_df["rating_average"], errors="coerce")
    valid = sold_df[rating.notna()].copy()
    valid["rating_average"] = rating[rating.notna()].values
    pub = (valid.groupby("publisher_vn")
           .agg(avg_rating=("rating_average","mean"),
                avg_sold=("all_time_quantity_sold","mean"),
                n=("all_time_quantity_sold","size"))
           .reset_index())
    pub = pub[pub["n"]>=5].copy()

    fig = px.scatter(pub, x="avg_rating", y="avg_sold", size="n",
                     hover_name="publisher_vn", size_max=40, opacity=0.7,
                     color="avg_sold", color_continuous_scale=[[0,"#c4b5fd"],[0.5,"#7c3aed"],[1,"#4c1d95"]],
                     labels={"avg_rating":"Rating TB","avg_sold":"Doanh số TB","n":"Số đầu sách"},
                     title="NXB: Chất lượng đánh giá vs Hiệu quả bán hàng")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      coloraxis_colorbar_title="DS TB", margin=dict(t=50,b=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- NXB nằm **phải + cao** → vừa chất lượng, vừa bán tốt.\n- Rating cao nhưng doanh số thấp → sách tốt nhưng chưa được tiếp cận rộng.")

# ---------------------------------------------------------------------------
# CHART 8 — Phân bổ giá theo Top NXB  (Box plot)
# ---------------------------------------------------------------------------

def _chart_publisher_price_box(df, colors):
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns or "price" not in sold_df.columns:
        st.info("Thiếu cột publisher_vn hoặc price."); return
    price = pd.to_numeric(sold_df["price"], errors="coerce")
    valid = sold_df[price.notna()].copy()
    valid["price"] = price[price.notna()].values
    top_pubs = (valid.groupby("publisher_vn")["all_time_quantity_sold"].sum()
                .sort_values(ascending=False).head(10).index.tolist())
    plot_df = valid[valid["publisher_vn"].isin(top_pubs)].copy()
    plot_df["publisher_vn"] = pd.Categorical(plot_df["publisher_vn"], categories=top_pubs, ordered=True)

    fig = px.box(plot_df, x="publisher_vn", y="price", color="publisher_vn",
                 color_discrete_sequence=px.colors.qualitative.Set2,
                 labels={"publisher_vn":"NXB","price":"Giá (₫)"},
                 title="Phân bổ giá sách theo Top 10 NXB (theo tổng doanh số)")
    fig.update_layout(showlegend=False, xaxis_tickangle=-30,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=50,b=10))
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- NXB có box hẹp → chiến lược giá **đồng nhất**.\n- Box rộng → danh mục đa dạng từ bình dân đến cao cấp.\n- Median thấp + doanh số cao → chiến lược **giá rẻ hút khách**.")

# ---------------------------------------------------------------------------
# CHART 9 — NXB: Doanh thu ước tính  (Grouped Bar)
# ---------------------------------------------------------------------------

def _chart_publisher_revenue(df, colors):
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns or "price" not in sold_df.columns:
        st.info("Thiếu dữ liệu."); return
    price = pd.to_numeric(sold_df["price"], errors="coerce").fillna(0)
    sold_df["revenue"] = price * sold_df["all_time_quantity_sold"]
    pub = (sold_df.groupby("publisher_vn")
           .agg(total_sold=("all_time_quantity_sold","sum"),
                total_rev=("revenue","sum"),
                n=("all_time_quantity_sold","size"))
           .reset_index())
    pub = pub.sort_values("total_rev", ascending=False).head(12)

    fig = make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=pub["publisher_vn"], y=pub["total_rev"],
                         name="Doanh thu ước tính (₫)", marker_color=colors[0], opacity=0.8,
                         text=pub["total_rev"].apply(_fmt_k), textposition="outside"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=pub["publisher_vn"], y=pub["total_sold"],
                             name="Tổng lượng bán", mode="lines+markers",
                             line=dict(color=colors[1],width=2), marker=dict(size=7)),
                  secondary_y=True)
    fig.update_layout(title="Top 12 NXB — Doanh thu ước tính & Tổng lượng bán",
                      xaxis_tickangle=-35,
                      legend=dict(orientation="h",y=1.12,x=0.5,xanchor="center"),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(t=55,b=80))
    fig.update_yaxes(title_text="Doanh thu (₫)", secondary_y=False)
    fig.update_yaxes(title_text="Tổng lượng bán", secondary_y=True)
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown("- NXB doanh thu cao nhưng lượng bán thấp → bán sách **giá cao**.\n- NXB lượng bán cao nhưng doanh thu thấp → chiến lược **số lượng lớn, giá thấp**.")


# ===========================================================================
# MAIN RENDER
# ===========================================================================

def render_publisher_author_tab(
    df: pd.DataFrame, *, colors: list[str], heatmap_scale: str,
) -> None:
    st.markdown("<div class='tab-page-header'>Tab 3 — NXB & Tác giả</div>", unsafe_allow_html=True)

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
        ("Doanh thu ước tính", f"{_fmt_k(est_rev)} ₫", "money", "slate"),
    ])

    # ── SECTION 1: NHÀ XUẤT BẢN ──
    _section("PHÂN TÍCH NHÀ XUẤT BẢN", "🏢")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_top_publishers(df, colors)       # Chart 1
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_publisher_donut(df, colors)       # Chart 2
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _chart_publisher_bubble(df, colors)          # Chart 3
    st.markdown("</div>", unsafe_allow_html=True)

    # ── SECTION 2: TÁC GIẢ ──
    _section("PHÂN TÍCH TÁC GIẢ", "✍️")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _chart_author_pareto(df, colors)             # Chart 4
    st.markdown("</div>", unsafe_allow_html=True)

    col_c, col_d = st.columns([1, 1])
    with col_c:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_top_books(df, colors)             # Chart 5
        st.markdown("</div>", unsafe_allow_html=True)
    with col_d:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_author_consistency(df, colors)    # Chart 6
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SECTION 3: INSIGHT SÂU ──
    _section("INSIGHT NÂNG CAO", "🔍")

    col_e, col_f = st.columns(2)
    with col_e:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_publisher_rating(df, colors)      # Chart 7
        st.markdown("</div>", unsafe_allow_html=True)
    with col_f:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _chart_publisher_price_box(df, colors)   # Chart 8
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _chart_publisher_revenue(df, colors)         # Chart 9
    st.markdown("</div>", unsafe_allow_html=True)
