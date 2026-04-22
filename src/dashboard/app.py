from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st

if __package__ in {None, ""}:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from dashboard.components.data_loader import default_data_path, load_dataset
    from dashboard.components.filter_ui import render_top_filters
    from dashboard.tabs import (
        render_distribution_product_tab,
        render_price_discount_tab,
        render_publisher_author_tab,
        render_rating_policy_tab,
    )
else:
    from .components.data_loader import default_data_path, load_dataset
    from .components.filter_ui import render_top_filters
    from .tabs import (
        render_distribution_product_tab,
        render_price_discount_tab,
        render_publisher_author_tab,
        render_rating_policy_tab,
    )


NORMAL_COLORS = px.colors.qualitative.Plotly
COLORBLIND_COLORS = [
    "#0077BB",
    "#EE7733",
    "#009988",
    "#CC3311",
    "#33BBEE",
    "#EE3377",
    "#BBBBBB",
]

TAB_OPTIONS = {
    "distribution": {"icon": "⌂", "label": "Phân bổ & Sản phẩm"},
    "price": {"icon": "◔", "label": "Giá & Chiết khấu"},
    "publisher": {"icon": "◎", "label": "NXB & Tác giả"},
    "rating": {"icon": "✦", "label": "Đánh giá & Chính sách"},
}


def _inject_style() -> None:
    css_path = Path(__file__).with_name("style.css")
    css_content = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def _get_active_tab() -> str:
    raw_value = st.query_params.get("tab", "distribution")
    selected = raw_value[0] if isinstance(raw_value, list) else raw_value
    if selected not in TAB_OPTIONS:
        selected = "distribution"
    return selected


def _get_colorblind_mode() -> bool:
    raw_value = st.query_params.get("cb", "0")
    selected = raw_value[0] if isinstance(raw_value, list) else raw_value
    return str(selected).strip() in {"1", "true", "True", "on"}


def _render_floating_tab_rail(active_tab: str) -> None:
    item_blocks: list[str] = []
    for tab_key, tab_meta in TAB_OPTIONS.items():
        active_class = " is-active" if tab_key == active_tab else ""
        item_blocks.append(
            (
                f'<a class="book-tab-link{active_class}" href="?tab={tab_key}" target="_self">'
                f'<span class="book-tab-icon">{tab_meta["icon"]}</span>'
                f'<span class="book-tab-label">{tab_meta["label"]}</span>'
                "</a>"
            )
        )

    st.markdown(
        "<div class='book-tab-rail'>" + "".join(item_blocks) + "</div>",
        unsafe_allow_html=True,
    )


def _render_fixed_header(active_tab: str, colorblind_mode: bool, total_books: int) -> None:
    target_state = "0" if colorblind_mode else "1"
    toggle_label = "Bật chế độ mù màu" if not colorblind_mode else "Tắt chế độ mù màu"
    toggle_href = f"?tab={active_tab}&cb={target_state}"

    st.markdown(
        f"""
        <div class="dashboard-head">
            <div class="hdr-left">
                <div class="hdr-logo">📚</div>
                <div>
                    <div class="hdr-school">PlotTwist · Nhóm phân tích dữ liệu</div>
                    <div class="hdr-title">Phân tích các yếu tố ảnh hưởng đến hiệu quả bán hàng sách</div>
                </div>
            </div>
            <div class="hdr-right">
                <div class="hdr-stat">
                    <div class="hdr-stat-val">{total_books:,}</div>
                    <div class="hdr-stat-lbl">Đầu sách</div>
                </div>
                <a class="hdr-badge" href="{toggle_href}" target="_self">
                    <div class="hdr-badge-val">👁</div>
                    <div class="hdr-badge-lbl">{toggle_label}</div>
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    numeric_cols = [
        "price",
        "discount_rate",
        "rating_average",
        "review_count",
        "all_time_quantity_sold",
    ]
    for col in numeric_cols:
        if col in view.columns:
            view[col] = pd.to_numeric(view[col], errors="coerce")

    if "publication_year" not in view.columns and "publication_date" in view.columns:
        view["publication_date"] = pd.to_datetime(view["publication_date"], errors="coerce")
        view["publication_year"] = view["publication_date"].dt.year

    return view


def _render_kpis(df: pd.DataFrame) -> None:
    sold = pd.to_numeric(df.get("all_time_quantity_sold"), errors="coerce")
    price = pd.to_numeric(df.get("price"), errors="coerce")
    rating = pd.to_numeric(df.get("rating_average"), errors="coerce")

    sold_non_null = sold.dropna() if sold is not None else pd.Series(dtype=float)
    revenue = float((price.fillna(0) * sold.fillna(0)).sum()) if price is not None else 0.0
    avg_sold = float(sold_non_null.mean()) if not sold_non_null.empty else 0.0
    avg_rating = float(rating.dropna().mean()) if rating is not None and rating.notna().any() else 0.0

    if "publisher_vn" in df.columns:
        n_publishers = int(df["publisher_vn"].nunique())
    else:
        n_publishers = 0

    revenue_fmt = f"{revenue:,.0f}"
    avg_sold_fmt = f"{avg_sold:,.1f}"
    avg_rating_fmt = f"{avg_rating:.2f}"

    st.markdown(
        f"""
        <div class="kpi-strip">
            <div class="kpi-box accent-blue">
                <div class="kpi-lbl">Tổng doanh thu ước tính</div>
                <div class="kpi-val">{revenue_fmt} <span class="u">VND</span></div>
            </div>
            <div class="kpi-box accent-amber">
                <div class="kpi-lbl">Lượng bán trung bình</div>
                <div class="kpi-val">{avg_sold_fmt}</div>
            </div>
            <div class="kpi-box accent-red">
                <div class="kpi-lbl">Điểm rating trung bình</div>
                <div class="kpi-val">{avg_rating_fmt}</div>
            </div>
            <div class="kpi-box accent-slate">
                <div class="kpi-lbl">Số nhà xuất bản</div>
                <div class="kpi-val">{n_publishers:,}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="PlotTwist - Dashboard phân tích sách",
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    pio.templates.default = "plotly_white"
    _inject_style()
    active_tab = _get_active_tab()
    colorblind_mode = _get_colorblind_mode()

    try:
        raw_df = load_dataset(str(default_data_path()))
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    st.sidebar.markdown(" ")
    _render_floating_tab_rail(active_tab)
    _render_fixed_header(active_tab, colorblind_mode, total_books=len(raw_df))

    df = _prepare_data(raw_df)
    st.markdown("<div style='margin-top:-1.35rem;'></div>", unsafe_allow_html=True)
    filtered_df = render_top_filters(df)

    if filtered_df.empty:
        st.warning("Bộ lọc hiện tại không có dữ liệu. Hãy mở rộng phạm vi lọc để tiếp tục.")
        st.stop()

    colors = COLORBLIND_COLORS if colorblind_mode else NORMAL_COLORS
    heatmap_scale = "Viridis" if colorblind_mode else "Blues"

    _render_kpis(filtered_df)

    if active_tab == "distribution":
        render_distribution_product_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "price":
        render_price_discount_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "publisher":
        render_publisher_author_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    else:
        render_rating_policy_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)


if __name__ == "__main__":
    main()
