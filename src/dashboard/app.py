from __future__ import annotations

from datetime import datetime
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
        render_overview_tab,
        render_price_discount_tab,
        render_publisher_author_tab,
        render_rating_crowd_tab,
        render_rating_seller_tab,
    )
else:
    from .components.data_loader import default_data_path, load_dataset
    from .components.filter_ui import render_top_filters
    from .tabs import (
        render_distribution_product_tab,
        render_overview_tab,
        render_price_discount_tab,
        render_publisher_author_tab,
        render_rating_crowd_tab,
        render_rating_seller_tab,
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
    "overview": {"icon": '<i class="fa-solid fa-chart-pie"></i>', "label": "Tổng quan"},
    "distribution": {"icon": '<i class="fa-solid fa-layer-group"></i>', "label": "Sản phẩm"},
    "price": {"icon": '<i class="fa-solid fa-tags"></i>', "label": "Giá & Chiết khấu"},
    "publisher": {"icon": '<i class="fa-solid fa-building-columns"></i>', "label": "NXB & Tác giả"},
    "rating_crowd": {"icon": '<i class="fa-solid fa-users-viewfinder"></i>', "label": "Hiệu ứng đám đông"},
    "rating_seller": {"icon": '<i class="fa-solid fa-truck-fast"></i>', "label": "Chiến lược seller"},
}


def _inject_style() -> None:
    st.markdown(
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>',
        unsafe_allow_html=True,
    )
    css_path = Path(__file__).with_name("style.css")
    css_content = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

    # Inject JavaScript to persist colorblind mode in localStorage
    st.markdown(
        """
        <script>
        (function() {
            const CB_KEY = 'plottwist_colorblind';
            const params = new URLSearchParams(window.location.search);
            const cbParam = params.get('cb');

            // If cb param is present, save it to localStorage
            if (cbParam !== null) {
                localStorage.setItem(CB_KEY, cbParam);
            } else {
                // If no cb param, restore from localStorage
                const stored = localStorage.getItem(CB_KEY);
                if (stored === '1') {
                    // Add cb=1 to URL and reload
                    params.set('cb', '1');
                    const newUrl = window.location.pathname + '?' + params.toString();
                    window.location.replace(newUrl);
                }
            }
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def _get_active_tab() -> str:
    raw_value = st.query_params.get("tab", "overview")
    selected = raw_value[0] if isinstance(raw_value, list) else raw_value
    if selected not in TAB_OPTIONS:
        selected = "distribution"
    return selected


def _get_colorblind_mode() -> bool:
    raw_value = st.query_params.get("cb", "0")
    selected = raw_value[0] if isinstance(raw_value, list) else raw_value
    return str(selected).strip() in {"1", "true", "True", "on"}


def _render_floating_tab_rail(active_tab: str, colorblind_mode: bool) -> None:
    cb_suffix = "&cb=1" if colorblind_mode else ""
    item_blocks: list[str] = []
    for tab_key, tab_meta in TAB_OPTIONS.items():
        active_class = " is-active" if tab_key == active_tab else ""
        item_blocks.append(
            (
                f'<a class="book-tab-link{active_class}" href="?tab={tab_key}{cb_suffix}" target="_self">'
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
    updated_at = datetime.now().strftime("%H:%M %d/%m/%Y")

    # JS snippet: when clicking the toggle, also update localStorage
    toggle_js = f"localStorage.setItem('plottwist_colorblind', '{target_state}');"

    st.markdown(
        f"""
        <div class="dashboard-head">
            <div class="hdr-left">
                <div class="hdr-logo"><i class="fa-solid fa-book"></i></div>
                <div>
                    <div class="hdr-title">Phân tích các yếu tố ảnh hưởng đến hiệu quả bán hàng sách trên nền tảng trực tuyến Nhà sách Tiki</div>
                </div>
            </div>
            <div class="hdr-right">
                <div class="hdr-actions">
                    <div class="hdr-stat">
                        <div class="hdr-stat-val"></div>
                        <div class="hdr-stat-lbl"></div>
                    </div>
                    <a class="hdr-badge" href="{toggle_href}" target="_self" onclick="{toggle_js}">
                        <div class="hdr-badge-val">👁</div>
                        <div class="hdr-badge-lbl">{toggle_label}</div>
                    </a>
                </div>
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
    _render_floating_tab_rail(active_tab, colorblind_mode)
    _render_fixed_header(active_tab, colorblind_mode, total_books=len(raw_df))

    df = _prepare_data(raw_df)
    filtered_df = render_top_filters(df)

    if filtered_df.empty:
        st.warning("Bộ lọc hiện tại không có dữ liệu. Hãy mở rộng phạm vi lọc để tiếp tục.")
        st.stop()

    colors = COLORBLIND_COLORS if colorblind_mode else NORMAL_COLORS
    heatmap_scale = "Viridis" if colorblind_mode else "Blues"

    if active_tab == "overview":
        render_overview_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "distribution":
        render_distribution_product_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "price":
        render_price_discount_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "publisher":
        render_publisher_author_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "rating_crowd":
        render_rating_crowd_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    elif active_tab == "rating_seller":
        render_rating_seller_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)
    else:
        render_distribution_product_tab(filtered_df, colors=colors, heatmap_scale=heatmap_scale)


if __name__ == "__main__":
    main()
