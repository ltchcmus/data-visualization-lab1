from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub


def _apply_black_text(fig) -> None:
    fig.update_layout(
        font={"color": "#000000"},
        title={"font": {"color": "#000000"}},
    )
    fig.update_xaxes(title_font={"color": "#000000"}, tickfont={"color": "#000000"})
    fig.update_yaxes(title_font={"color": "#000000"}, tickfont={"color": "#000000"})


def _render_kpi_row(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div style="background:linear-gradient(105deg,#dcedff 0%,#eff6ff 52%,#ffffff 100%);border:1px solid #cfe0f2;border-radius:10px;padding:10px 12px;box-shadow:0 8px 18px rgba(31,79,125,0.12);">
                    <div style="font-size:0.78rem;font-weight:700;color:#173a5e;opacity:0.9;">{label}</div>
                    <div style="margin-top:4px;font-size:1.25rem;font-weight:800;color:#000000;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _q5_discount_threshold(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "discount_rate" not in sold_df.columns:
        st.info("Không có cột discount_rate.")
        return

    disc = pd.to_numeric(sold_df["discount_rate"], errors="coerce")
    sold_df = sold_df[disc.notna()].copy()
    sold_df["discount_rate"] = disc[disc.notna()].values

    bins = [-1, 0, 10, 20, 30, 50, 100]
    labels = ["0%", "1–10%", "11–20%", "21–30%", "31–50%", ">50%"]
    sold_df["discount_bin"] = pd.cut(
        sold_df["discount_rate"], bins=bins, labels=labels, right=True
    )

    agg = (
        sold_df.groupby("discount_bin", observed=True)
        .agg(avg_sold=("all_time_quantity_sold", "mean"), count=("all_time_quantity_sold", "size"))
        .reset_index()
    )
    agg["pct_books"] = agg["count"] / agg["count"].sum() * 100

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=agg["discount_bin"].astype(str),
            y=agg["avg_sold"],
            name="Lượng bán TB",
            marker_color=colors[0],
            opacity=0.85,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=agg["discount_bin"].astype(str),
            y=agg["pct_books"],
            name="% số sách",
            mode="lines+markers",
            line={"color": colors[1], "width": 2},
            marker={"size": 7},
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Q5 — Ngưỡng giảm giá & Doanh số",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": -0.2},
    )
    fig.update_yaxes(title_text="Lượng bán trung bình", secondary_y=False)
    fig.update_yaxes(title_text="% số sách trong nhóm", secondary_y=True)
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Biểu đồ kết hợp Bar–Line giúp xem đồng thời **mức doanh số trung bình** và **mật độ** sách trong từng nhóm discount.
- Nhóm có discount cao không nhất thiết bán tốt nhất — có thể phản ánh sách cũ/tồn kho được giảm giá.
- Ngưỡng "điểm bùng phát" (nếu có) sẽ là nhóm có avg_sold tăng vọt bất thường so với nhóm kề cận.
"""
        )


def _q9_year_trend(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "publication_year" not in sold_df.columns:
        st.info("Không có cột publication_year.")
        return

    year_col = pd.to_numeric(sold_df["publication_year"], errors="coerce")
    valid = sold_df[year_col.between(1900, 2025)].copy()
    valid["publication_year"] = year_col[year_col.between(1900, 2025)].astype(int).values

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
        title="Q9 — Doanh số trung bình theo năm xuất bản",
        xaxis_title="Năm xuất bản",
        yaxis_title="Lượng bán trung bình",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": -0.2},
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Sách **xuất bản gần đây** có thể có doanh số cao hơn do được đặt trên kệ nổi bật hơn, nhưng sách cũ có nhiều thời gian tích lũy đơn hàng.
- Đường trung bình động (3 năm) làm mịn biến động ngẫu nhiên, giúp thấy **xu hướng dài hạn** rõ hơn.
- Nếu sách cổ điển (>10 năm) vẫn duy trì doanh số, đó là dấu hiệu của "sách vượt thời gian" đáng đầu tư dài hạn.
"""
        )


def render_price_discount_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown("<div class='tab-page-header'>Tab 2 — Giá & Chiết khấu</div>", unsafe_allow_html=True)

    sold_df = _filter_sold(df)
    disc = pd.to_numeric(sold_df.get("discount_rate", pd.Series(dtype=float)), errors="coerce")

    avg_disc = float(disc.dropna().mean()) if disc.notna().any() else 0.0
    pct_discounted = float((disc > 0).sum() / len(disc) * 100) if len(disc) > 0 else 0.0
    _render_kpi_row(
        [
            ("Sách có doanh số > 0", f"{len(sold_df):,}"),
            ("Discount trung bình", f"{avg_disc:.1f}%"),
            ("Tỷ lệ có giảm giá", f"{pct_discounted:.1f}%"),
        ]
    )

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q5_discount_threshold(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q9_year_trend(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
