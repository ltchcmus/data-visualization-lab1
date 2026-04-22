from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st


COOL_TONE_COLORS = ["#1E3A8A", "#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD"]


def _inject_tab1_chart_card_style() -> None:
    st.markdown(
        """
        <style>
        .tab1-chart-card {
            border: 1px solid #dbe7f2;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: 0 8px 18px rgba(31, 79, 125, 0.10);
            padding: 10px 12px 8px;
            margin: 6px 0 12px;
        }
        .tab1-chart-head {
            border: 1px solid #cfe0f2;
            border-radius: 10px;
            background: linear-gradient(105deg, #dcedff 0%, #eff6ff 52%, #ffffff 100%);
            box-shadow: 0 8px 18px rgba(31, 79, 125, 0.12);
            padding: 10px 12px;
            margin: 0 0 10px;
        }
        .tab1-chart-title {
            color: #0f2740;
            font-weight: 700;
            font-size: 0.95rem;
            line-height: 1.35;
        }
        .tab1-chart-sub {
            margin-top: 2px;
            color: #4b6785;
            font-size: 0.82rem;
            line-height: 1.35;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_chart_card_start(title: str | None = None, subtitle: str | None = None) -> None:
    st.markdown("<div class='tab1-chart-card'>", unsafe_allow_html=True)
    clean_title = (title or "").strip()
    clean_subtitle = (subtitle or "").strip()
    if not clean_title and not clean_subtitle:
        return

    parts = ["<div class='tab1-chart-head'>"]
    if clean_title:
        parts.append(f"<div class='tab1-chart-title'>{html.escape(clean_title)}</div>")
    if clean_subtitle:
        parts.append(f"<div class='tab1-chart-sub'>{html.escape(clean_subtitle)}</div>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def _render_chart_card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


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
        title=None,
        title_text=None,
        margin={"t": 36},
    )
    fig.update_xaxes(title_font={"color": "#000000"}, tickfont={"color": "#000000"})
    fig.update_yaxes(title_font={"color": "#000000"}, tickfont={"color": "#000000"})


def _q1_long_tail(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    _render_chart_card_start("Q1 — Phân bổ doanh số: Hiệu ứng Long-tail")
    fig = px.histogram(
        sold_df,
        x="all_time_quantity_sold",
        nbins=80,
        log_y=True,
        color_discrete_sequence=[colors[0]],
        labels={"all_time_quantity_sold": "Lượng bán (all-time)", "count": "Số đầu sách (log)"},
    )
    fig.update_layout(
        bargap=0.05,
        xaxis_title="Lượng bán (all-time)",
        yaxis_title="Số đầu sách (thang log)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    _render_chart_card_end()


def _q2_category_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    col = "cat_level_3" if "cat_level_3" in sold_df.columns else "cat_level_2"
    if col not in sold_df.columns:
        st.info("Không có cột danh mục để vẽ boxplot.")
        return

    _render_chart_card_start("Q2 — Hiệu quả bán hàng theo thể loại (Top 15)")

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
        showlegend=False,
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    _render_chart_card_end()


def _q10_pages_vs_sold(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "number_of_page" not in sold_df.columns:
        st.info("Không có cột số trang để vẽ scatter.")
        return

    _render_chart_card_start("Q10 — Độ dày sách vs Doanh số")

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
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    _render_chart_card_end()


def render_distribution_product_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    _inject_tab1_chart_card_style()
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
            ("Sách có doanh số > 0", f"{len(sold_df):,}"),
            ("Doanh số trung vị", f"{median_sold:,}"),
            ("Top 1% sách chiếm", f"{top1_pct:.1f}% doanh số"),
        ]
    )

    col_a, col_b = st.columns(2)
    with col_a:
        _q1_long_tail(df, colors)
    with col_b:
        _q2_category_boxplot(df, colors)

    _q10_pages_vs_sold(df, colors)
