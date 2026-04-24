from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ..format_utils import apply_chart_style, format_vn
from ..ml_integration import render_chart_with_ml, render_chat_section
from ..ui_cards import render_kpi_section, render_metric_strip


def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub



def _fmt_ty(value: float) -> str:
    """Format large VND value in tỷ (billion), e.g. 728.4 Tỷ."""
    ty = value / 1_000_000_000
    return format_vn(ty, 1) + " Tỷ"


def _render_kpis(df: pd.DataFrame) -> None:
    sold = pd.to_numeric(df.get("all_time_quantity_sold"), errors="coerce")
    price = pd.to_numeric(df.get("price"), errors="coerce")
    rating = pd.to_numeric(df.get("rating_average"), errors="coerce")

    revenue = float((price.fillna(0) * sold.fillna(0)).sum()) if price is not None else 0.0

    valid_ratings = rating.dropna() if rating is not None else pd.Series(dtype=float)
    avg_rating = float(valid_ratings.mean()) if not valid_ratings.empty else 0.0

    n_publishers = int(df["publisher_vn"].nunique()) if "publisher_vn" in df.columns else 0

    author_col = next((c for c in ("primary_author", "authors") if c in df.columns), None)
    n_authors = int(df[author_col].nunique()) if author_col else 0

    pct_authentic = 0.0
    if "is_authentic" in df.columns:
        auth = df["is_authentic"]
        valid_auth = auth.notna()
        if valid_auth.any():
            pct_authentic = float(auth[valid_auth].eq(True).sum() / valid_auth.sum() * 100)

    rating_benchmark = (
        "Cao hơn mức kỳ vọng của người mua." if avg_rating >= 4.0 else "Thấp hơn mức kỳ vọng của người mua."
    )
    rating_tone = "red" if avg_rating < 4.0 else "blue"

    render_kpi_section(
        [
            {
                "label": "Tổng doanh thu (Est.)",
                "value": f"{_fmt_ty(revenue)} <span class='u'>VND</span>",
                "icon": "money",
                "tone": "blue",
                "subtitle": "Ước tính từ giá × lượng bán.",
            },
            {
                "label": "Tổng số đầu sách",
                "value": format_vn(len(df)),
                "icon": "book",
                "tone": "slate",
                "subtitle": f"Từ {format_vn(n_publishers)} NXB trên toàn quốc.",
            },
            {
                "label": "Số tác giả",
                "value": format_vn(n_authors),
                "icon": "users",
                "tone": "amber",
                "subtitle": "Tổng số tác giả trong danh mục.",
            },
            {
                "label": "Điểm rating trung bình",
                "value": format_vn(avg_rating, 2),
                "icon": "star",
                "tone": rating_tone,
                "subtitle": rating_benchmark,
            },
            {
                "label": "% Sách chính hãng",
                "value": f"{format_vn(pct_authentic, 1)}%",
                "icon": "target",
                "tone": "emerald",
                "subtitle": "Tỷ lệ sách có nguồn gốc chính hãng.",
            },
        ],
        title="CHỈ SỐ TỔNG QUAN",
        summary="Cái nhìn toàn cảnh về quy mô danh mục, hiệu quả kinh doanh và chất lượng sản phẩm.",
        footnote=f"Dữ liệu được tổng hợp từ {format_vn(n_publishers)} nhà xuất bản, {format_vn(n_authors)} tác giả.",
    )


def _q1_long_tail(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    fig = px.histogram(
        sold_df,
        x="all_time_quantity_sold",
        nbins=80,
        log_y=True,
        color_discrete_sequence=[colors[0]],
        labels={"all_time_quantity_sold": "Lượng bán", "count": "Số đầu sách (log)"},
    )
    fig.update_layout(
        title="Phân bổ doanh số: Hiệu ứng Long-tail",
        bargap=0.05,
        xaxis_title="Lượng bán",
        yaxis_title="Số đầu sách (log)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig)
    render_chart_with_ml("overview_long_tail", fig, df, label="Phân bổ doanh số")


def render_overview_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    # st.markdown(
    #     "<div class='tab-page-header'>"
    #     "<p class='tph-title'>Tổng quan thị trường sách</p>"
    #     "<p class='tph-sub'>Nhìn toàn cảnh hiệu suất kinh doanh — doanh thu, lượng bán và phân bổ doanh số trên toàn bộ danh mục.</p>"
    #     "</div>",
    #     unsafe_allow_html=True,
    # )

    _render_kpis(df)

    sold_df = _filter_sold(df)
    n_sold = len(sold_df)
    median_sold = int(sold_df["all_time_quantity_sold"].median()) if n_sold > 0 else 0
    top1_pct = (
        sold_df.nlargest(max(1, int(n_sold * 0.01)), "all_time_quantity_sold")[
            "all_time_quantity_sold"
        ].sum()
        / sold_df["all_time_quantity_sold"].sum()
        * 100
    ) if n_sold > 0 else 0.0

    pct_freeship = 0.0
    if "has_freeship" in df.columns:
        fs = df["has_freeship"]
        valid_fs = fs.notna()
        if valid_fs.any():
            pct_freeship = float(fs[valid_fs].eq(True).sum() / valid_fs.sum() * 100)

    n_sellers = int(df["current_seller_name"].nunique()) if "current_seller_name" in df.columns else 0

    render_metric_strip(
        [
            {"label": "Sách có doanh số > 0", "value": format_vn(n_sold), "icon": "book", "tone": "blue"},
            {"label": "Doanh số trung vị", "value": format_vn(median_sold), "icon": "chart", "tone": "amber"},
            {"label": "Top 1% sách chiếm", "value": f"{format_vn(top1_pct, 1)}% doanh số", "icon": "target", "tone": "blue"},
            {"label": "Số người bán", "value": format_vn(n_sellers), "icon": "building", "tone": "slate"},
        ],
        compact=True,
        cols=4,
    )

    _q1_long_tail(df, colors)

    # ── ML Chat / Ask AI section ──────────────────────────────────
    render_chat_section(df)

    st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)