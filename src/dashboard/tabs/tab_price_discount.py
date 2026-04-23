from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ..format_utils import apply_chart_style, format_vn
from ..ui_cards import render_metric_strip


def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub



def _render_kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    render_metric_strip(
        [
            {"label": label, "value": value, "icon": icon, "tone": tone}
            for label, value, icon, tone in items
        ],
        compact=True,
    )


def _q5_discount_threshold(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "discount_rate" not in sold_df.columns:
        st.info("Không có cột discount_rate.")
        return

    disc = pd.to_numeric(sold_df["discount_rate"], errors="coerce")
    sold_df = sold_df[disc.notna()].copy()
    sold_df["discount_rate"] = disc[disc.notna()].values

    if "price" in sold_df.columns:
        price = pd.to_numeric(sold_df["price"], errors="coerce").fillna(0)
        sold_df["revenue"] = price * sold_df["all_time_quantity_sold"]
    else:
        sold_df["revenue"] = 0

    bins = [-1, 0, 10, 20, 30, 50, 75, 100]
    labels = ["0%", "1–10%", "11–20%", "21–30%", "31–50%", "51–75%", ">75%"]
    sold_df["discount_bin"] = pd.cut(
        sold_df["discount_rate"], bins=bins, labels=labels, right=True
    )

    agg = (
        sold_df.groupby("discount_bin", observed=True)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            total_sold=("all_time_quantity_sold", "sum"),
            total_revenue=("revenue", "sum"),
            count=("all_time_quantity_sold", "size")
        )
        .reset_index()
    )
    agg["pct_books"] = agg["count"] / agg["count"].sum() * 100
    total_rev_sum = agg["total_revenue"].sum()
    agg["pct_revenue"] = (agg["total_revenue"] / total_rev_sum * 100) if total_rev_sum > 0 else 0

    c1 = colors[0] if len(colors) > 0 else "#3b82f6"
    c2 = colors[1] if len(colors) > 1 else "#ef4444"
    c3 = colors[2] if len(colors) > 2 else "#10b981"

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    def format_k_m(n):
        if pd.isna(n):
            return ""
        if n >= 1e6:
            return f"{format_vn(n / 1e6, 1)}M"
        if n >= 1e3:
            return f"{format_vn(n / 1e3, 1)}K"
        return format_vn(n)

    # 1. Bar chart 1: Lượng bán TB (Trục trái)
    fig.add_trace(
        go.Bar(
            x=agg["discount_bin"].astype(str),
            y=agg["avg_sold"],
            name="Lượng bán TB",
            marker_color=c1,
            opacity=0.85,
            text=agg["avg_sold"].apply(format_k_m),
            textposition="outside",
            textfont=dict(size=11),
            hovertemplate="<b>Mức giảm: %{x}</b><br>Lượng bán TB: %{y:,.0f} cuốn<extra></extra>"
        ),
        secondary_y=False,
    )

    # 2. Bar chart 2: Tổng lượng bán (Trục trái)
    c4 = colors[3] if len(colors) > 3 else "#f59e0b"
    fig.add_trace(
        go.Bar(
            x=agg["discount_bin"].astype(str),
            y=agg["total_sold"],
            name="Tổng lượng bán",
            marker_color=c4,
            opacity=0.85,
            text=agg["total_sold"].apply(format_k_m),
            textposition="outside",
            textfont=dict(size=11),
            hovertemplate="<b>Mức giảm: %{x}</b><br>Tổng lượng bán: %{y:,.0f} cuốn<extra></extra>"
        ),
        secondary_y=False,
    )
    
    # 3. Line chart 1: % Số lượng sách (Trục phải)
    fig.add_trace(
        go.Scatter(
            x=agg["discount_bin"].astype(str),
            y=agg["pct_books"],
            name="% Số lượng sách",
            mode="lines+markers",
            line={"color": c2, "width": 2},
            marker={"size": 7},
            hovertemplate="Tỷ trọng sách: %{y:.1f}%<extra></extra>"
        ),
        secondary_y=True,
    )

    # 4. Line chart 2: % Tổng doanh thu (Trục phải)
    fig.add_trace(
        go.Scatter(
            x=agg["discount_bin"].astype(str),
            y=agg["pct_revenue"],
            name="% Doanh thu",
            mode="lines+markers",
            line={"color": c3, "width": 2, "dash": "dot"},
            marker={"size": 7, "symbol": "diamond"},
            hovertemplate="Tỷ trọng doanh thu: %{y:.1f}%<br>(Tổng giá trị: %{customdata:,.0f} ₫)<extra></extra>",
            customdata=agg["total_revenue"]
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Tương quan giữa Mức giảm giá, Doanh số & Doanh thu",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": -0.2},
        hovermode="x unified",
        barmode="group",
        margin=dict(t=50, b=0)
    )
    # Using log scale for left Y-axis since Total Sold (M) and Avg Sold (K) have large magnitude difference
    fig.update_yaxes(title_text="Lượng bán (cuốn) - Log Scale", type="log", secondary_y=False)
    fig.update_yaxes(title_text="Tỷ trọng (%)", secondary_y=True)
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- Biểu đồ kết hợp Bar-Line giúp xem đồng thời **mức doanh số trung bình** (Bar) và sự phân bổ **Mật độ sách** cùng **Tổng doanh thu** (Line) trong từng nhóm discount.
- Nhóm có discount cao không nhất thiết bán tốt nhất — có thể phản ánh sách cũ/tồn kho được giảm giá.
- Ngưỡng "điểm bùng phát" (nếu có) sẽ là nhóm có lượng bán trung bình tăng vọt bất thường.
- Đường % Doanh thu cho phép đánh giá xem phần lớn dòng tiền đến từ ngưỡng giảm giá nào, qua đó tìm ra mức giảm giá tối ưu nhất để tối đa hoá doanh thu.
"""
        )


def _q9_year_trend(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "publication_year" not in sold_df.columns:
        st.info("Không có cột publication_year.")
        return

    year_col = pd.to_numeric(sold_df["publication_year"], errors="coerce")
    valid = sold_df[year_col.between(2000, 2025)].copy()
    valid["publication_year"] = year_col[year_col.between(2000, 2025)].astype(int).values

    yearly = (
        valid.groupby("publication_year")["all_time_quantity_sold"]
        .mean()
        .reset_index()
        .sort_values("publication_year")
    )
    yearly["rolling_avg"] = yearly["all_time_quantity_sold"].rolling(3, center=True, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=yearly["publication_year"],
            y=yearly["all_time_quantity_sold"],
            name="Doanh số TB",
            marker_color=colors[0],
            opacity=0.75,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=yearly["publication_year"],
            y=yearly["rolling_avg"],
            name="Trung bình động (3 năm)",
            mode="lines",
            line={"color": colors[1], "width": 2.5},
        )
    )
    fig.update_layout(
        title="Doanh số trung bình theo năm xuất bản",
        xaxis_title="Năm xuất bản",
        yaxis_title="Lượng bán trung bình",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": -0.2},
        margin=dict(t=50, b=0),
    )
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- Sách **xuất bản gần đây** có thể có doanh số cao hơn do được đặt trên kệ nổi bật hơn, nhưng sách cũ có nhiều thời gian tích lũy đơn hàng.
- Đường trung bình động (3 năm) làm mịn biến động ngẫu nhiên, giúp thấy **xu hướng dài hạn** rõ hơn.
- Nếu sách cổ điển (>10 năm) vẫn duy trì doanh số, đó là dấu hiệu của "sách vượt thời gian" đáng đầu tư dài hạn.
"""
        )


def _q10_price_year_trend(df: pd.DataFrame, colors: list[str]) -> None:
    """Biểu đồ giá trung bình & số lượng sách theo năm xuất bản."""
    if "publication_year" not in df.columns:
        st.info("Không có cột publication_year.")
        return
    if "price" not in df.columns:
        st.info("Không có cột price.")
        return

    year_col = pd.to_numeric(df["publication_year"], errors="coerce")
    price_col = pd.to_numeric(df["price"], errors="coerce")
    mask = year_col.between(2000, 2025) & price_col.notna()
    valid = df[mask].copy()
    valid["publication_year"] = year_col[mask].astype(int).values
    valid["price"] = price_col[mask].values

    yearly = (
        valid.groupby("publication_year")
        .agg(
            avg_price=("price", "mean"),
            count=("price", "size"),
        )
        .reset_index()
        .sort_values("publication_year")
    )
    yearly["price_rolling"] = yearly["avg_price"].rolling(3, center=True, min_periods=1).mean()

    c_bar = colors[2] if len(colors) > 2 else "#10b981"
    c_line = colors[3] if len(colors) > 3 else "#f59e0b"

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=yearly["publication_year"],
            y=yearly["count"],
            name="Số đầu sách",
            marker_color=c_bar,
            opacity=0.7,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=yearly["publication_year"],
            y=yearly["avg_price"],
            name="Giá TB",
            mode="markers",
            marker={"color": c_line, "size": 5},
            hovertemplate="Giá TB: %{y:,.0f} ₫<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=yearly["publication_year"],
            y=yearly["price_rolling"],
            name="Giá TB động (3 năm)",
            mode="lines",
            line={"color": c_line, "width": 2.5},
            hovertemplate="Giá TB động: %{y:,.0f} ₫<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Giá trung bình & số đầu sách theo năm xuất bản",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": -0.2},
        margin=dict(t=50, b=0),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Số đầu sách", secondary_y=False)
    fig.update_yaxes(title_text="Giá trung bình (₫)", secondary_y=True)
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- Biểu đồ cho thấy **xu hướng giá bán** sách thay đổi như thế nào qua từng năm, kết hợp với **khối lượng xuất bản**.
- Nếu giá tăng nhưng số lượng sách giảm, có thể thị trường đang **chuyển sang phân khúc cao cấp hơn**.
- Đường trung bình động giúp loại bỏ biến động ngắn hạn, cho thấy **xu hướng giá dài hạn** rõ ràng hơn.
- Năm có nhiều đầu sách nhưng giá thấp có thể phản ánh giai đoạn **cạnh tranh giá gay gắt**.
"""
        )


def render_price_discount_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    # st.markdown(
    #     "<div class='tab-page-header'>"
    #     "<p class='tph-title'>Phân tích Giá & Chiết khấu</p>"
    #     "<p class='tph-sub'>Đánh giá tác động của mức giá và mức chiết khấu đến doanh số — tìm ngưỡng tối ưu để tối đa hoá hiệu quả bán hàng.</p>"
    #     "</div>",
    #     unsafe_allow_html=True,
    # )

    sold_df = _filter_sold(df)
    disc = pd.to_numeric(sold_df.get("discount_rate", pd.Series(dtype=float)), errors="coerce")

    avg_disc = float(disc.dropna().mean()) if disc.notna().any() else 0.0
    pct_discounted = float((disc > 0).sum() / len(disc) * 100) if len(disc) > 0 else 0.0
    _render_kpi_row(
        [
            ("Sách có doanh số > 0", format_vn(len(sold_df)), "book", "blue"),
            ("Discount trung bình", f"{format_vn(avg_disc, 1)}%", "tag", "amber"),
            ("Tỷ lệ có giảm giá", f"{format_vn(pct_discounted, 1)}%", "percent", "blue"),
        ]
    )

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q5_discount_threshold(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _q9_year_trend(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _q10_price_year_trend(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)
