from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ..format_utils import format_vn
from ..ui_cards import render_kpi_section, render_metric_strip


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


def _render_kpis(df: pd.DataFrame) -> None:
    sold = pd.to_numeric(df.get("all_time_quantity_sold"), errors="coerce")
    price = pd.to_numeric(df.get("price"), errors="coerce")
    rating = pd.to_numeric(df.get("rating_average"), errors="coerce")

    sold_non_null = sold.dropna() if sold is not None else pd.Series(dtype=float)
    revenue = float((price.fillna(0) * sold.fillna(0)).sum()) if price is not None else 0.0
    avg_sold = float(sold_non_null.mean()) if not sold_non_null.empty else 0.0

    valid_ratings = rating.dropna() if rating is not None else pd.Series(dtype=float)
    valid_ratings = valid_ratings[valid_ratings > 0]
    avg_rating = float(valid_ratings.mean()) if not valid_ratings.empty else 0.0

    n_publishers = int(df["publisher_vn"].nunique()) if "publisher_vn" in df.columns else 0

    rating_benchmark = (
        "Cao hơn mức trung bình ngành (4.0)." if avg_rating >= 4.0 else "Thấp hơn mức trung bình ngành (4.0)."
    )
    rating_tone = "red" if avg_rating < 4.0 else "blue"

    render_kpi_section(
        [
            {
                "label": "Tổng doanh thu ước tính",
                "value": f"{format_vn(revenue, 0)} <span class='u'>VND</span>",
                "icon": "money",
                "tone": "blue",
                "subtitle": "Ước tính từ giá × lượng bán.",
            },
            {
                "label": "Lượng bán trung bình",
                "value": format_vn(avg_sold, 1),
                "icon": "chart",
                "tone": "amber",
                "subtitle": "Mức bán trung bình ổn định.",
            },
            {
                "label": "Điểm rating trung bình",
                "value": format_vn(avg_rating, 2),
                "icon": "star",
                "tone": rating_tone,
                "subtitle": rating_benchmark,
            },
            {
                "label": "Số nhà xuất bản",
                "value": format_vn(n_publishers),
                "icon": "book",
                "tone": "slate",
                "subtitle": "Phạm vi dữ liệu toàn quốc.",
            },
        ],
        title="CHỈ SỐ BÁN HÀNG CỐT LÕI",
        summary="Hiệu quả bán hàng đang duy trì ở mức ổn định với doanh thu đạt ngưỡng mục tiêu.",
        footnote=f"Dữ liệu được tổng hợp từ {format_vn(n_publishers)} nhà xuất bản trên toàn quốc.",
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
        title="Phân bổ doanh số: Hiệu ứng Long-tail",
        bargap=0.05,
        xaxis_title="Lượng bán (all-time)",
        yaxis_title="Số đầu sách (thang log)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(":material/notes: Nhận xét"):
        st.markdown(
            """
- Phân bổ doanh số cho thấy hiệu ứng **Long-tail** rõ rệt: đa số sách bán rất ít, chỉ một số ít bán chạy vượt trội.
- Thang log giúp nhận diện các "tầng" doanh số khác nhau mà thang tuyến tính khó thấy.
- Đây là cơ sở quan trọng để phân nhóm sách theo mức độ bán chạy.
"""
        )


def render_overview_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown(
        "<div class='tab-page-header'>"
        "<p class='tph-title'>Tổng quan thị trường sách</p>"
        "<p class='tph-sub'>Nhìn toàn cảnh hiệu suất kinh doanh — doanh thu, lượng bán và phân bổ doanh số trên toàn bộ danh mục.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

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

    render_metric_strip(
        [
            {"label": "Sách có doanh số > 0", "value": format_vn(n_sold), "icon": "book", "tone": "blue"},
            {"label": "Doanh số trung vị", "value": format_vn(median_sold), "icon": "chart", "tone": "amber"},
            {"label": "Top 1% sách chiếm", "value": f"{format_vn(top1_pct, 1)}% doanh số", "icon": "target", "tone": "blue"},
        ],
        compact=True,
    )

    st.caption("Biểu đồ dùng thang log ở trục tung để giảm ảnh hưởng của outliers.")
    _q1_long_tail(df, colors)
