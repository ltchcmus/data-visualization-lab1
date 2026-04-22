from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ..format_utils import format_vn
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


def _apply_black_text(fig) -> None:
    fig.update_layout(
        font={"color": "#000000"},
        title={"font": {"color": "#000000"}},
        margin={"t": 56},
    )
    fig.update_xaxes(
        title_font={"color": "#000000"},
        tickfont={"color": "#000000"},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )
    fig.update_yaxes(
        title_font={"color": "#000000"},
        tickfont={"color": "#000000"},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )


def _q1_long_tail(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    fig = px.histogram(
        sold_df,
        x="all_time_quantity_sold",
        nbins=80,
        log_y=True,
        color_discrete_sequence=[colors[0]],
        labels={"all_time_quantity_sold": "Lượng bán (all-time)", "count": "Số đầu sách (log)"},
    )
    fig.update_layout(
        title="Q1 — Phân bổ doanh số: Hiệu ứng Long-tail",
        bargap=0.05,
        xaxis_title="Lượng bán (all-time)",
        yaxis_title="Số đầu sách (thang log)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)


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
        color_discrete_sequence=[COOL_TONE_COLORS[1]],
        labels={col: "Thể loại", "all_time_quantity_sold": "Lượng bán (log)"},
    )
    fig.update_layout(
        title="Q2 — Hiệu quả bán hàng theo thể loại (Top 15)",
        showlegend=False,
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)


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
        color_discrete_sequence=COOL_TONE_COLORS,
        category_orders={"page_group": group_order},
        trendline="ols",
        log_y=True,
        opacity=0.55,
        labels={
            "number_of_page": "Số trang",
            "all_time_quantity_sold": "Lượng bán (log)",
            "page_group": "Nhóm số trang",
        },
    )
    fig.update_layout(
        title="Q10 — Độ dày sách vs Doanh số",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_distribution_product_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown("<div class='tab-page-header'>Tab 1 — Phân bổ & Sản phẩm</div>", unsafe_allow_html=True)

    sold_df = _filter_sold(df)
    median_sold = int(sold_df["all_time_quantity_sold"].median())
    top1_pct = (
        sold_df.nlargest(int(len(sold_df) * 0.01), "all_time_quantity_sold")[
            "all_time_quantity_sold"
        ].sum()
        / sold_df["all_time_quantity_sold"].sum()
        * 100
    )
    _render_kpi_row(
        [
            ("Sách có doanh số > 0", format_vn(len(sold_df)), "book", "blue"),
            ("Doanh số trung vị", format_vn(median_sold), "chart", "amber"),
            ("Top 1% sách chiếm", f"{format_vn(top1_pct, 1)}% doanh số", "target", "red"),
        ]
    )

    st.caption("Lưu ý: Q1 và Q2 dùng thang log ở trục tung để giảm ảnh hưởng của outliers.")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _q1_long_tail(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        _q2_category_boxplot(df, colors)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q10_pages_vs_sold(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
