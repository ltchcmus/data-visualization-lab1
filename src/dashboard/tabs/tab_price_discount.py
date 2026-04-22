from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def _sold_view(df: pd.DataFrame) -> pd.DataFrame:
    required = {"discount_rate", "all_time_quantity_sold"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    view = df.copy()
    view["discount_rate"] = pd.to_numeric(view["discount_rate"], errors="coerce")
    view["all_time_quantity_sold"] = pd.to_numeric(
        view["all_time_quantity_sold"], errors="coerce"
    )
    view = view.dropna(subset=["discount_rate", "all_time_quantity_sold"])
    view = view[view["all_time_quantity_sold"] > 0]
    return view


def _discount_threshold_chart(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    if sold_df.empty:
        st.info("Không đủ dữ liệu để phân tích ngưỡng giảm giá.")
        return

    sold_df["discount_bin"] = pd.cut(
        sold_df["discount_rate"],
        bins=list(range(0, 105, 5)),
        labels=[f"{i}-{i + 5}%" for i in range(0, 100, 5)],
        right=False,
    )

    agg = (
        sold_df.groupby("discount_bin", observed=False)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            total_sold=("all_time_quantity_sold", "sum"),
        )
        .reset_index()
        .dropna(subset=["discount_bin"])
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=agg["discount_bin"],
            y=agg["avg_sold"],
            marker_color=colors[0],
            name="TB lượng bán",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=agg["discount_bin"],
            y=agg["total_sold"],
            mode="lines+markers",
            marker_color=colors[1],
            line=dict(color=colors[1], width=3),
            name="Tổng lượng bán",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Q5. Ngưỡng giảm giá và hiệu quả doanh số",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    fig.update_xaxes(title="Nhóm discount")
    fig.update_yaxes(title_text="TB lượng bán", secondary_y=False)
    fig.update_yaxes(title_text="Tổng lượng bán", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _year_trend_chart(df: pd.DataFrame, colors: list[str]) -> None:
    required = {"publication_year", "all_time_quantity_sold"}
    if not required.issubset(df.columns):
        st.info("Không đủ dữ liệu để vẽ xu hướng theo năm xuất bản.")
        return

    view = df.copy()
    view["publication_year"] = pd.to_numeric(view["publication_year"], errors="coerce")
    view["all_time_quantity_sold"] = pd.to_numeric(
        view["all_time_quantity_sold"], errors="coerce"
    )
    view = view.dropna(subset=["publication_year", "all_time_quantity_sold"])
    view = view[view["all_time_quantity_sold"] > 0]

    if view.empty:
        st.info("Không có dữ liệu năm xuất bản hợp lệ.")
        return

    yearly = (
        view.groupby("publication_year")["all_time_quantity_sold"]
        .mean()
        .reset_index(name="avg_sold")
        .sort_values("publication_year")
    )
    yearly["rolling_3"] = yearly["avg_sold"].rolling(3, min_periods=1).mean()

    fig = go.Figure()
    fig.add_bar(
        x=yearly["publication_year"],
        y=yearly["avg_sold"],
        marker_color=colors[2],
        name="TB lượng bán",
    )
    fig.add_scatter(
        x=yearly["publication_year"],
        y=yearly["rolling_3"],
        mode="lines+markers",
        line=dict(color=colors[1], width=3),
        name="Rolling mean (3 năm)",
    )
    fig.update_layout(
        title="Q9. Xu hướng doanh số theo năm xuất bản",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    fig.update_xaxes(title="Năm xuất bản")
    fig.update_yaxes(title="all_time_quantity_sold trung bình")
    st.plotly_chart(fig, use_container_width=True)


def render_price_discount_tab(
    df: pd.DataFrame,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    _ = heatmap_scale
    st.subheader("Tab 2 - Giá và chiết khấu")

    col_a, col_b = st.columns(2)
    with col_a:
        _discount_threshold_chart(df, colors)
    with col_b:
        _year_trend_chart(df, colors)

    with st.expander("Nhận xét"):
        st.markdown(
            "- Biểu đồ kết hợp giúp tìm vùng discount tối ưu thay vì chỉ nhìn tỷ lệ giảm giá cao nhất.\n"
            "- So sánh đường xu hướng theo năm cho thấy khác biệt giữa nhóm sách mới và nhóm sách phát hành lâu năm.\n"
            "- Nên đọc kết quả cùng số lượng đầu sách từng năm để tránh kết luận thiên lệch do cỡ mẫu."
        )
