from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


def _sold_view(df: pd.DataFrame) -> pd.DataFrame:
    required = {"all_time_quantity_sold", "authors", "publisher_vn"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    view = df.copy()
    view["all_time_quantity_sold"] = pd.to_numeric(
        view["all_time_quantity_sold"], errors="coerce"
    )
    view["price"] = pd.to_numeric(view.get("price"), errors="coerce")
    view = view.dropna(subset=["all_time_quantity_sold"])
    view = view[view["all_time_quantity_sold"] > 0]
    view["revenue"] = view["price"].fillna(0) * view["all_time_quantity_sold"]
    return view


def _publisher_top_chart(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    if sold_df.empty:
        st.info("Không đủ dữ liệu để vẽ top nhà xuất bản.")
        return

    pub_stats = (
        sold_df.groupby("publisher_vn")
        .agg(avg_sold=("all_time_quantity_sold", "mean"), book_count=("publisher_vn", "size"))
        .query("book_count >= 5")
        .sort_values("avg_sold", ascending=False)
        .head(15)
        .reset_index()
    )

    if pub_stats.empty:
        st.info("Không có nhà xuất bản đạt điều kiện tối thiểu 5 đầu sách.")
        return

    fig = px.bar(
        pub_stats.sort_values("avg_sold"),
        x="avg_sold",
        y="publisher_vn",
        orientation="h",
        color_discrete_sequence=[colors[0]],
        title="Q3. Top nhà xuất bản theo doanh số trung bình",
    )
    fig.add_vline(
        x=float(sold_df["all_time_quantity_sold"].mean()),
        line_dash="dash",
        line_color=colors[1],
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
    fig.update_xaxes(title="all_time_quantity_sold trung bình")
    fig.update_yaxes(title="publisher_vn")
    st.plotly_chart(fig, use_container_width=True)


def _author_pareto_chart(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    if sold_df.empty:
        st.info("Không đủ dữ liệu để vẽ Pareto tác giả.")
        return

    top_authors = (
        sold_df.groupby("authors", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
        .head(20)
    )
    top_authors["cum_pct"] = top_authors["revenue"].cumsum() / top_authors["revenue"].sum() * 100

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=top_authors["authors"],
            y=top_authors["revenue"],
            marker_color=colors[2],
            name="Doanh thu",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=top_authors["authors"],
            y=top_authors["cum_pct"],
            mode="lines+markers",
            line=dict(color=colors[1], width=3),
            name="% tích lũy",
        ),
        secondary_y=True,
    )
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color=colors[0],
        secondary_y=True,
    )
    fig.update_layout(
        title="Q4/Q6. Pareto tác giả theo doanh thu",
        margin=dict(l=10, r=10, t=60, b=10),
    )
    fig.update_xaxes(title="authors", tickangle=-35)
    fig.update_yaxes(title_text="Doanh thu", secondary_y=False)
    fig.update_yaxes(title_text="% tích lũy", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def _author_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _sold_view(df)
    if sold_df.empty:
        st.info("Không đủ dữ liệu để vẽ boxplot theo tác giả.")
        return

    top_names = (
        sold_df.groupby("authors")["all_time_quantity_sold"]
        .sum()
        .sort_values(ascending=False)
        .head(12)
        .index.tolist()
    )
    box_df = sold_df[sold_df["authors"].isin(top_names)]
    if box_df.empty:
        st.info("Không có dữ liệu boxplot cho nhóm tác giả top.")
        return

    fig = px.box(
        box_df,
        x="authors",
        y="all_time_quantity_sold",
        points="outliers",
        color="authors",
        color_discrete_sequence=colors,
        title="Độ ổn định doanh số của nhóm tác giả top",
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
    fig.update_xaxes(title="authors", tickangle=-35)
    fig.update_yaxes(title="all_time_quantity_sold")
    st.plotly_chart(fig, use_container_width=True)


def render_publisher_author_tab(
    df: pd.DataFrame,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    _ = heatmap_scale
    st.subheader("Tab 3 - Nhà xuất bản và tác giả")

    col_a, col_b = st.columns(2)
    with col_a:
        _publisher_top_chart(df, colors)
    with col_b:
        _author_pareto_chart(df, colors)

    _author_boxplot(df, colors)

    with st.expander("Nhận xét"):
        st.markdown(
            "- Top NXB theo doanh số trung bình giúp nhìn ra nhóm đối tác chiến lược, đồng thời đã lọc nhiễu bằng ngưỡng số đầu sách tối thiểu.\n"
            "- Pareto cho thấy mức độ tập trung doanh thu theo tác giả và kiểm tra trực tiếp giả thuyết 80/20.\n"
            "- Boxplot tác giả top giúp phân biệt tác giả bán đều hay phụ thuộc một vài đầu sách hit."
        )
