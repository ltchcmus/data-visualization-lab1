from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    return view


def _bubble_chart(df: pd.DataFrame, colors: list[str]) -> None:
    required = {"rating_average", "review_count", "all_time_quantity_sold"}
    sold_df = _sold_view(df)
    if sold_df.empty or not required.issubset(sold_df.columns):
        st.info("Không đủ dữ liệu cho bubble chart rating và review.")
        return

    sample_df = sold_df.copy()
    sample_df["rating_average"] = pd.to_numeric(sample_df["rating_average"], errors="coerce")
    sample_df["review_count"] = pd.to_numeric(sample_df["review_count"], errors="coerce")
    sample_df = sample_df.dropna(subset=["rating_average", "review_count"])

    if len(sample_df) > 2500:
        sample_df = sample_df.sample(2500, random_state=42)

    max_sold = max(float(sample_df["all_time_quantity_sold"].max()), 1.0)
    sample_df["bubble_size"] = (sample_df["all_time_quantity_sold"] / max_sold * 45).clip(lower=6)

    fig = px.scatter(
        sample_df,
        x="rating_average",
        y="review_count",
        size="bubble_size",
        color_discrete_sequence=[colors[0]],
        opacity=0.6,
        log_y=True,
        hover_data=["name"] if "name" in sample_df.columns else None,
        title="Q7. Rating và review_count tác động đến sales",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
    fig.update_xaxes(title="rating_average")
    fig.update_yaxes(title="review_count (log scale)")
    st.plotly_chart(fig, use_container_width=True)


def _correlation_heatmap(df: pd.DataFrame, heatmap_scale: str) -> None:
    cols = [
        "price",
        "discount_rate",
        "rating_average",
        "review_count",
        "all_time_quantity_sold",
        "number_of_page",
    ]
    numeric_cols = [col for col in cols if col in df.columns]
    if len(numeric_cols) < 3:
        st.info("Không đủ cột số để vẽ heatmap tương quan.")
        return

    corr = df[numeric_cols].apply(pd.to_numeric, errors="coerce").corr()
    fig = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            zmin=-1,
            zmax=1,
            colorscale=heatmap_scale,
            text=np.round(corr.values, 2),
            texttemplate="%{text}",
        )
    )
    fig.update_layout(
        title="Heatmap tương quan các biến số chính",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


def _freeship_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    required = {"has_freeship", "all_time_quantity_sold"}
    if sold_df.empty or not required.issubset(sold_df.columns):
        st.info("Không đủ dữ liệu để so sánh freeship.")
        return

    sold_df["freeship_label"] = sold_df["has_freeship"].map({True: "Freeship", False: "Không freeship"})
    sold_df["freeship_label"] = sold_df["freeship_label"].fillna("Không xác định")

    fig = px.violin(
        sold_df,
        x="freeship_label",
        y="all_time_quantity_sold",
        color="freeship_label",
        color_discrete_sequence=colors,
        box=True,
        points="outliers",
        log_y=True,
        title="Q8. So sánh doanh số theo chính sách freeship",
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(title="has_freeship")
    fig.update_yaxes(title="all_time_quantity_sold (log scale)")
    st.plotly_chart(fig, use_container_width=True)


def _seller_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    required = {"current_seller_name", "all_time_quantity_sold"}
    if sold_df.empty or not required.issubset(sold_df.columns):
        st.info("Không đủ dữ liệu để so sánh nhà bán.")
        return

    top_sellers = (
        sold_df.groupby("current_seller_name")["all_time_quantity_sold"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )
    compare_df = sold_df[sold_df["current_seller_name"].isin(top_sellers)]

    fig = px.box(
        compare_df,
        x="current_seller_name",
        y="all_time_quantity_sold",
        color="current_seller_name",
        color_discrete_sequence=colors,
        points="outliers",
        log_y=True,
        title="So sánh phân bổ doanh số của top 5 seller",
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(title="current_seller_name", tickangle=-25)
    fig.update_yaxes(title="all_time_quantity_sold (log scale)")
    st.plotly_chart(fig, use_container_width=True)


def render_rating_policy_tab(
    df: pd.DataFrame,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.subheader("Tab 4 - Đánh giá và chính sách")

    col_a, col_b = st.columns(2)
    with col_a:
        _bubble_chart(df, colors)
    with col_b:
        _correlation_heatmap(df, heatmap_scale)

    col_c, col_d = st.columns(2)
    with col_c:
        _freeship_boxplot(df, colors)
    with col_d:
        _seller_boxplot(df, colors)

    with st.expander("Nhận xét"):
        st.markdown(
            "- Bubble chart cho thấy hiệu ứng cộng hưởng giữa rating cao và nhiều review trong việc kéo doanh số.\n"
            "- Heatmap hỗ trợ định lượng mức tương quan thay vì chỉ nhìn trực giác từ biểu đồ rời rạc.\n"
            "- Violin/boxplot cho freeship và seller giúp đánh giá lợi thế vận hành của từng nhóm bán hàng."
        )
