from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def _sold_view(df: pd.DataFrame) -> pd.DataFrame:
    if "all_time_quantity_sold" not in df.columns:
        return pd.DataFrame()

    view = df.copy()
    view["all_time_quantity_sold"] = pd.to_numeric(
        view["all_time_quantity_sold"], errors="coerce"
    )
    view = view.dropna(subset=["all_time_quantity_sold"])
    view = view[view["all_time_quantity_sold"] > 0]

    if view.empty:
        return view

    cap = float(view["all_time_quantity_sold"].quantile(0.99))
    view["sold_capped"] = view["all_time_quantity_sold"].clip(upper=cap)
    return view


def _distribution_chart(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    if sold_df.empty:
        st.info("Không đủ dữ liệu để vẽ phân bổ doanh số.")
        return

    fig = px.histogram(
        sold_df,
        x="all_time_quantity_sold",
        nbins=50,
        log_y=True,
        color_discrete_sequence=[colors[0]],
        title="Q1. Phân bổ doanh số và hiệu ứng long-tail",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(title="all_time_quantity_sold")
    fig.update_yaxes(title="Tần suất (log scale)")
    st.plotly_chart(fig, use_container_width=True)


def _category_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    if sold_df.empty or "cat_level_2" not in sold_df.columns:
        st.info("Không đủ dữ liệu để vẽ boxplot theo danh mục.")
        return

    fig = px.box(
        sold_df,
        x="cat_level_2",
        y="sold_capped",
        points="outliers",
        color="cat_level_2",
        color_discrete_sequence=colors,
        title="Q2. Hiệu quả bán hàng theo danh mục",
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(title="Danh mục cấp 2")
    fig.update_yaxes(title="all_time_quantity_sold (capped p99)")
    st.plotly_chart(fig, use_container_width=True)


def _pages_vs_sales(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    required = {"number_of_page", "all_time_quantity_sold"}
    if sold_df.empty or not required.issubset(sold_df.columns):
        st.info("Không đủ dữ liệu để vẽ tương quan độ dày sách và doanh số.")
        return

    sold_df["number_of_page"] = pd.to_numeric(sold_df["number_of_page"], errors="coerce")
    sold_df = sold_df.dropna(subset=["number_of_page"])
    if sold_df.empty:
        st.info("Không có dữ liệu hợp lệ cho số trang sách.")
        return

    bins = [0, 100, 300, 500, np.inf]
    labels = ["<100", "100-300", "300-500", ">500"]
    sold_df["page_group"] = pd.cut(sold_df["number_of_page"], bins=bins, labels=labels)

    fig = px.scatter(
        sold_df,
        x="number_of_page",
        y="all_time_quantity_sold",
        color="page_group",
        color_discrete_sequence=colors,
        trendline="ols",
        trendline_color_override=colors[1],
        log_y=True,
        hover_data=["name"] if "name" in sold_df.columns else None,
        title="Q10. Độ dày sách và doanh số",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(title="number_of_page")
    fig.update_yaxes(title="all_time_quantity_sold (log scale)")
    st.plotly_chart(fig, use_container_width=True)


def render_distribution_product_tab(
    df: pd.DataFrame,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    _ = heatmap_scale
    st.subheader("Tab 1 - Phân bổ và sản phẩm")

    col_a, col_b = st.columns(2)
    with col_a:
        _distribution_chart(df, colors)
    with col_b:
        _category_boxplot(df, colors)

    _pages_vs_sales(df, colors)

    with st.expander("Nhận xét"):
        st.markdown(
            "- Phân phối lệch phải cho thấy long-tail rõ rệt: phần lớn đầu sách bán ít, một số ít bán rất cao.\n"
            "- So sánh boxplot giúp nhận ra danh mục có doanh số trung vị tốt và danh mục có nhiều best-seller outlier.\n"
            "- Tương quan số trang và lượng bán thường không tuyến tính mạnh, cần kết hợp thêm giá và mức giảm giá để kết luận."
        )
