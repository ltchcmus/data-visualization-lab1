from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub


def _q3_top_publishers(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns:
        st.info("Không có cột publisher_vn.")
        return

    pub_agg = (
        sold_df.groupby("publisher_vn")
        .agg(avg_sold=("all_time_quantity_sold", "mean"), book_count=("all_time_quantity_sold", "size"))
        .reset_index()
    )
    pub_agg = pub_agg[pub_agg["book_count"] >= 5].sort_values("avg_sold", ascending=True).tail(15)

    overall_avg = float(sold_df["all_time_quantity_sold"].mean())

    fig = px.bar(
        pub_agg,
        x="avg_sold",
        y="publisher_vn",
        orientation="h",
        color="avg_sold",
        color_continuous_scale=[[0, colors[0]], [1, colors[1]]],
        labels={"avg_sold": "Lượng bán trung bình", "publisher_vn": "Nhà xuất bản"},
        title="Q3 — Top 15 NXB theo doanh số trung bình (≥5 đầu sách)",
        text="avg_sold",
    )
    fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside")
    fig.add_vline(
        x=overall_avg,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"TB toàn dataset: {overall_avg:,.0f}",
        annotation_position="top right",
    )
    fig.update_layout(
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Chỉ lấy NXB có **≥5 đầu sách** để tránh bias từ NXB có 1–2 cuốn may mắn bán chạy.
- Đường trung bình dataset phân tách rõ nhóm NXB "trên ngưỡng" và "dưới ngưỡng" thị trường.
- NXB dẫn đầu thường là đơn vị lớn có hệ thống phân phối, marketing, hoặc tập trung vào thể loại hot (sách giáo dục, self-help).
"""
        )


def _q4_author_pareto(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "authors" not in sold_df.columns:
        st.info("Không có cột authors.")
        return

    author_agg = (
        sold_df.groupby("authors")["all_time_quantity_sold"]
        .sum()
        .reset_index()
        .sort_values("all_time_quantity_sold", ascending=False)
        .head(30)
    )
    author_agg["cumulative_pct"] = (
        author_agg["all_time_quantity_sold"].cumsum()
        / author_agg["all_time_quantity_sold"].sum()
        * 100
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=author_agg["authors"],
            y=author_agg["all_time_quantity_sold"],
            name="Tổng lượng bán",
            marker_color=colors[0],
            opacity=0.85,
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=author_agg["authors"],
            y=author_agg["cumulative_pct"],
            name="% tích lũy",
            mode="lines+markers",
            line={"color": colors[1], "width": 2},
            marker={"size": 6},
            yaxis="y2",
        )
    )
    fig.add_hline(
        y=80,
        line_dash="dot",
        line_color="red",
        annotation_text="80%",
        annotation_position="right",
        yref="y2",
    )
    fig.update_layout(
        title="Q4/Q6 — Biểu đồ Pareto: Tác giả & Doanh số (Top 30)",
        xaxis={"tickangle": -40},
        yaxis={"title": "Tổng lượng bán"},
        yaxis2={"title": "% tích lũy", "overlaying": "y", "side": "right", "range": [0, 105]},
        legend={"orientation": "h", "y": -0.25},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Đường tích lũy qua ngưỡng **80%** cho thấy cần bao nhiêu tác giả hàng đầu để chiếm 80% tổng doanh số.
- Nếu đường cắt 80% sớm (ít tác giả) → thị trường **tập trung cao** — rủi ro nếu tác giả đó ngừng hoạt động.
- Tác giả có cột bar cao nhưng không phải 1 đầu sách duy nhất → "bán đều tay" trên nhiều tựa.
"""
        )


def render_publisher_author_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown("### Tab 3 — NXB & Tác giả")

    sold_df = _filter_sold(df)
    k1, k2, k3 = st.columns(3)
    with k1:
        n_pub = int(df["publisher_vn"].nunique()) if "publisher_vn" in df.columns else 0
        st.metric("Số NXB", f"{n_pub:,}")
    with k2:
        n_authors = int(df["authors"].nunique()) if "authors" in df.columns else 0
        st.metric("Số tác giả", f"{n_authors:,}")
    with k3:
        avg_sold = float(sold_df["all_time_quantity_sold"].mean())
        st.metric("Doanh số TB", f"{avg_sold:,.0f}")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q3_top_publishers(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q4_author_pareto(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
