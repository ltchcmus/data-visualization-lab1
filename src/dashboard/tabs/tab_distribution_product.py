from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ..format_utils import apply_chart_style, format_vn
from ..ml_integration import render_chart_with_ml
from ..ui_cards import render_metric_strip


COOL_TONE_COLORS = ["#1E3A8A", "#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD"]


def _render_kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    render_metric_strip(
        [
            {"label": label, "value": value, "icon": icon, "tone": tone}
            for label, value, icon, tone in items
        ],
        compact=True,
    )


def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub



def _q2_category_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    col = "cat_level_3" if "cat_level_3" in sold_df.columns else "cat_level_2"
    if col not in sold_df.columns:
        st.info("Không có cột danh mục để vẽ boxplot.")
        return

    medians = (
        sold_df.groupby(col)["all_time_quantity_sold"]
        .median()
        .sort_values(ascending=False)
    )
    top_cats = medians.head(15).index.tolist()
    plot_df = sold_df[sold_df[col].isin(top_cats)].copy()
    plot_df[col] = pd.Categorical(plot_df[col], categories=top_cats, ordered=True)

    fig = px.box(
        plot_df,
        x=col,
        y="all_time_quantity_sold",
        log_y=True,
        color_discrete_sequence=[colors[0] if colors else '#1D4ED8'],
        labels={col: "Thể loại", "all_time_quantity_sold": "Lượng bán"},
    )
    fig.update_layout(
        title="Hiệu quả bán hàng theo thể loại (Top 15)",
        showlegend=False,
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    render_chart_with_ml("dist_category_boxplot", fig, df, label="Boxplot thể loại")


def _q10_pages_vs_sold(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "number_of_page" not in sold_df.columns:
        st.info("Không có cột số trang để vẽ scatter.")
        return

    pages = pd.to_numeric(sold_df["number_of_page"], errors="coerce")
    valid = sold_df[pages.notna() & (pages > 0)].copy()
    valid["number_of_page"] = pages[pages.notna() & (pages > 0)].values

    def _page_group(p: float) -> str:
        if p < 100:
            return "<100 trang"
        if p < 300:
            return "100–300 trang"
        if p < 500:
            return "300–500 trang"
        return ">500 trang"

    valid["page_group"] = valid["number_of_page"].map(_page_group)
    group_order = ["<100 trang", "100–300 trang", "300–500 trang", ">500 trang"]

    fig = px.scatter(
        valid,
        x="number_of_page",
        y="all_time_quantity_sold",
        color="page_group",
        color_discrete_sequence=colors,
        category_orders={"page_group": group_order},
        trendline="ols",
        log_x=True,
        log_y=True,
        opacity=0.55,
        labels={
            "number_of_page": "Số trang",
            "all_time_quantity_sold": "Lượng bán",
            "page_group": "Nhóm số trang",
        },
    )
    fig.update_layout(
        title="Độ dày sách vs Doanh số",
        xaxis_title="Số trang",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    x_min = float(valid["number_of_page"].min())
    x_max = float(valid["number_of_page"].max())
    decade_ticks_x: list[int] = []
    tick_x = 1
    while tick_x * 10 <= max(1.0, x_min):
        tick_x *= 10
    while tick_x <= max(1.0, x_max):
        decade_ticks_x.append(tick_x)
        tick_x *= 10
    if not decade_ticks_x:
        decade_ticks_x = [1]

    y_max = float(valid["all_time_quantity_sold"].max())
    decade_ticks: list[int] = []
    tick = 1
    while tick <= max(1.0, y_max):
        decade_ticks.append(tick)
        tick *= 10
    if not decade_ticks:
        decade_ticks = [1]

    fig.update_yaxes(
        tickmode="array",
        tickvals=decade_ticks,
        ticktext=[format_vn(v, 0) for v in decade_ticks],
        minor=dict(showgrid=False),
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=decade_ticks_x,
        ticktext=[format_vn(v, 0) for v in decade_ticks_x],
        minor=dict(showgrid=False),
    )

    for trace in fig.data:
        if "markers" in str(getattr(trace, "mode", "")):
            trace.marker.size = 5

    apply_chart_style(fig)
    render_chart_with_ml("dist_pages_vs_sold", fig, df, label="Số trang vs Doanh số")


def _q12_niche_market(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    col = "cat_level_3" if "cat_level_3" in sold_df.columns else "cat_level_2"
    if col not in sold_df.columns:
        st.info("Không có cột danh mục để vẽ quadrant chart.")
        return

    rating = pd.to_numeric(sold_df.get("rating_average"), errors="coerce")
    sold_df = sold_df[rating.notna() & (rating > 0)].copy()
    sold_df["rating_average"] = pd.to_numeric(sold_df["rating_average"], errors="coerce")

    agg = (
        sold_df.groupby(col)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            avg_rating=("rating_average", "mean"),
            count=(col, "count"),
        )
        .reset_index()
    )
    agg = agg[agg["count"] >= 10].nlargest(15, "count")

    med_sold = agg["avg_sold"].median()
    med_rating = agg["avg_rating"].median()

    def _quadrant(row) -> str:
        high_s = row["avg_sold"] >= med_sold
        high_r = row["avg_rating"] >= med_rating
        if high_s and high_r:
            return "Ngôi sao"
        if not high_s and high_r:
            return "Tiềm năng"
        if high_s and not high_r:
            return "Phổ thông"
        return "Cần cải thiện"

    agg["quadrant"] = agg.apply(_quadrant, axis=1)

    quadrant_colors = {
        "Ngôi sao": colors[0] if len(colors) > 0 else "#2563EB",
        "Tiềm năng": colors[2] if len(colors) > 2 else "#16A34A",
        "Phổ thông": colors[1] if len(colors) > 1 else "#F59E0B",
        "Cần cải thiện": colors[3] if len(colors) > 3 else "#DC2626",
    }

    fig = px.scatter(
        agg,
        x="avg_sold",
        y="avg_rating",
        color="quadrant",
        color_discrete_map=quadrant_colors,
        size="count",
        size_max=40,
        text=col,
        labels={
            "avg_sold": "Doanh số trung bình",
            "avg_rating": "Rating trung bình",
            "quadrant": "Phân vùng",
            "count": "Số đầu sách",
        },
    )
    fig.add_vline(x=med_sold, line_dash="dash", line_color="#94A3B8", line_width=1)
    fig.add_hline(y=med_rating, line_dash="dash", line_color="#94A3B8", line_width=1)
    fig.update_traces(textposition="top center", textfont_size=9)
    fig.update_layout(
        title="Thị trường ngách: Phân vùng danh mục",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    render_chart_with_ml("dist_niche_market", fig, df, label="Thị trường ngách")


def _stacked_bar_genre_pages(df: pd.DataFrame, colors: list[str]) -> None:
    col = "cat_level_3" if "cat_level_3" in df.columns else "cat_level_2"
    if col not in df.columns or "number_of_page" not in df.columns:
        st.info("Không đủ dữ liệu để vẽ stacked bar chart.")
        return

    pages = pd.to_numeric(df["number_of_page"], errors="coerce")
    valid = df[pages.notna() & (pages > 0)].copy()
    valid["number_of_page"] = pages[pages.notna() & (pages > 0)].values

    def _page_group(p: float) -> str:
        if p < 100:
            return "<100 trang"
        if p < 300:
            return "100–300 trang"
        if p < 500:
            return "300–500 trang"
        return ">500 trang"

    group_order = ["<100 trang", "100–300 trang", "300–500 trang", ">500 trang"]
    valid["page_group"] = valid["number_of_page"].map(_page_group)

    top_cats = valid.groupby(col).size().nlargest(12).index.tolist()
    agg = (
        valid[valid[col].isin(top_cats)]
        .groupby([col, "page_group"])
        .size()
        .reset_index(name="count")
    )

    fig = px.bar(
        agg,
        x=col,
        y="count",
        color="page_group",
        barmode="stack",
        color_discrete_sequence=colors,
        category_orders={"page_group": group_order, col: top_cats},
        labels={col: "Thể loại", "count": "Số đầu sách", "page_group": "Nhóm số trang"},
    )
    fig.update_layout(
        title="Phân bố số trang theo Thể loại (Top 12)",
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    render_chart_with_ml("dist_genre_pages", fig, df, label="Số trang theo thể loại")


def render_distribution_product_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    sold_df = _filter_sold(df)
    pages_ratio = sold_df[(sold_df["number_of_page"] >= 100) & (sold_df["number_of_page"] <= 500)].shape[0] / len(sold_df) * 100
    median_sold = int(sold_df["all_time_quantity_sold"].median())
    top1_pct = (
        sold_df.nlargest(int(len(sold_df) * 0.01), "all_time_quantity_sold")[
            "all_time_quantity_sold"
        ].sum()
        / sold_df["all_time_quantity_sold"].sum()
        * 100
    )

    col_cat = "cat_level_3" if "cat_level_3" in sold_df.columns else "cat_level_2"
    _rating = pd.to_numeric(sold_df.get("rating_average"), errors="coerce")
    _niche_df = sold_df[_rating.notna() & (_rating > 0)].copy()
    _niche_df["rating_average"] = pd.to_numeric(_niche_df["rating_average"], errors="coerce")
    _agg = (
        _niche_df.groupby(col_cat)
        .agg(avg_sold=("all_time_quantity_sold", "mean"), avg_rating=("rating_average", "mean"), count=(col_cat, "count"))
        .reset_index()
    )
    _agg = _agg[_agg["count"] >= 10].nlargest(15, "count")
    _med_sold = _agg["avg_sold"].median()
    _med_rating = _agg["avg_rating"].median()
    num_potential = int(((_agg["avg_sold"] < _med_sold) & (_agg["avg_rating"] >= _med_rating)).sum())

    _render_kpi_row(
        [
            ("Tổng số thể loại", format_vn(len(sold_df)), "book", "blue"),
            ("Tỷ lệ sách 100-500 trang:", f"{format_vn(pages_ratio, 1)}%", "chart", "amber"),
            ("Số danh mục Tiềm năng", f"{num_potential}", "target", "blue"),
        ]
    )

    col_a, col_b = st.columns(2)
    with col_a:
        _q2_category_boxplot(df, colors)
    with col_b:
        _q12_niche_market(df, colors)

    col_c, col_d = st.columns(2)
    with col_c:
        _q10_pages_vs_sold(df, colors)
    with col_d:
        _stacked_bar_genre_pages(df, colors)
