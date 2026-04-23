from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ..format_utils import apply_chart_style, format_vn
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
        color_discrete_sequence=[COOL_TONE_COLORS[1]],
        labels={col: "Thể loại", "all_time_quantity_sold": "Lượng bán (log)"},
    )
    fig.update_layout(
        title="Hiệu quả bán hàng theo thể loại (Top 15)",
        showlegend=False,
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- Boxplot cho thấy **phân phối doanh số** thực sự trong từng thể loại, bao gồm cả outlier.
- Thể loại có hộp (box) rộng → doanh số dao động lớn; hộp hẹp → đồng đều hơn.
- So sánh median (đường ngang trong hộp) giữa các thể loại để tìm nhóm tiềm năng.
"""
        )


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
        title="Độ dày sách vs Doanh số",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- Scatter plot cho thấy mối quan hệ giữa **độ dày sách** và **doanh số bán**.
- Đường hồi quy (trendline) giúp nhận diện xu hướng chung: sách dày hơn có bán tốt hơn không?
- Nhóm màu theo khoảng trang giúp phân biệt rõ ràng các phân khúc sản phẩm.
"""
        )


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
    agg = agg[agg["count"] >= 5]

    med_sold = agg["avg_sold"].median()
    med_rating = agg["avg_rating"].median()

    def _quadrant(row) -> str:
        high_s = row["avg_sold"] >= med_sold
        high_r = row["avg_rating"] >= med_rating
        if high_s and high_r:
            return "Ngôi sao"
        if not high_s and high_r:
            return "Tiềm năng (Niche)"
        if high_s and not high_r:
            return "Phổ thông"
        return "Cần cải thiện"

    agg["quadrant"] = agg.apply(_quadrant, axis=1)

    quadrant_colors = {
        "Ngôi sao": "#2563EB",
        "Tiềm năng (Niche)": "#16A34A",
        "Phổ thông": "#F59E0B",
        "Cần cải thiện": "#DC2626",
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
        title="Thị trường ngách: Phân vùng danh mục (Sales vs Rating)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- **Ngôi sao** (High Sales / High Rating): thể loại phổ biến và được yêu thích — ưu tiên duy trì.
- **Tiềm năng (Niche)** (Low Sales / High Rating): sách chất lượng cao nhưng ít người biết — cơ hội marketing.
- **Phổ thông** (High Sales / Low Rating): bán chạy dù rating thấp — thường là sách giáo khoa, từ điển.
- **Cần cải thiện** (Low Sales / Low Rating): cần xem xét lại chiến lược sản phẩm.
- Kích thước điểm thể hiện số lượng đầu sách trong danh mục.
"""
        )


def render_distribution_product_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    # st.markdown(
    #     "<div class='tab-page-header'>"
    #     "<p class='tph-title'>Phân tích Đặc tính Sản phẩm</p>"
    #     "<p class='tph-sub'>Khám phá mối tương quan giữa thể loại, độ dày và hiệu quả kinh doanh của các đầu sách.</p>"
    #     "</div>",
    #     unsafe_allow_html=True,
    # )

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
            ("Tổng số thể loại", format_vn(len(sold_df)), "book", "blue"),
            ("Doanh số trung vị", format_vn(median_sold), "chart", "amber"),
            ("Top 1% sách chiếm", f"{format_vn(top1_pct, 1)}% doanh số", "target", "blue"),
        ]
    )

    col_a, col_b = st.columns(2)
    with col_a:
        _q2_category_boxplot(df, colors)
    with col_b:
        _q10_pages_vs_sold(df, colors)

    _q12_niche_market(df, colors)
