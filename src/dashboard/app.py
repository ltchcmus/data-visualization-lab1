from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

if __package__ in {None, ""}:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from dashboard.components.data_loader import default_data_path, load_dataset
    from dashboard.tabs import (
        render_distribution_product_tab,
        render_price_discount_tab,
        render_publisher_author_tab,
        render_rating_policy_tab,
    )
else:
    from .components.data_loader import default_data_path, load_dataset
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
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #eff5fb 0%, #f8fbff 60%, #eef3f9 100%);
        }

        :root {
            --left-sidebar-width: 100px;
            --content-left-gap: 14px;
        }

        [data-testid="stSidebar"] {
            width: var(--left-sidebar-width) !important;
            min-width: var(--left-sidebar-width) !important;
            max-width: var(--left-sidebar-width) !important;
            border-right: 1px solid #c8dced;
            background: linear-gradient(180deg, #d6e7f6 0%, #e8f2fb 100%);
            z-index: 220 !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            width: var(--left-sidebar-width) !important;
            min-width: var(--left-sidebar-width) !important;
            max-width: var(--left-sidebar-width) !important;
            background: linear-gradient(180deg, #d6e7f6 0%, #e8f2fb 100%);
            z-index: 220 !important;
        }

        .stApp [data-testid="stAppViewContainer"],
        .stApp [data-testid="stAppViewContainer"] .main {
            overflow: visible !important;
        }

        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            padding-top: 0.4rem;
            padding-left: 0.35rem;
            padding-right: 0.35rem;
        }

        [data-testid="collapsedControl"] {
            display: none !important;
        }

        .stApp [data-testid="stAppViewContainer"] .main .block-container {
            margin-left: 0 !important;
            padding-left: var(--content-left-gap) !important;
            padding-top: 7.2rem;
        }

        .dashboard-head {
            position: fixed;
            top: 10px;
            left: calc(var(--left-sidebar-width) + var(--content-left-gap));
            right: 14px;
            z-index: 1001;
            border-radius: 16px;
            background: linear-gradient(120deg, #0f2f53 0%, #1b4f82 45%, #2d77b1 100%);
            color: #ecf6ff;
            box-shadow: 0 10px 24px rgba(15, 47, 83, 0.24);
            border: 1px solid rgba(187, 216, 244, 0.22);
            padding: 14px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }

        .dashboard-head-meta {
            font-size: 0.85rem;
            color: #cde4f8;
            margin: 0;
        }

        .dashboard-head-title {
            font-size: 2rem;
            line-height: 1.12;
            font-weight: 700;
            margin: 2px 0 0;
        }

        .dashboard-head-toggle {
            text-decoration: none;
            color: #e8f4ff;
            border: 1px solid rgba(220, 238, 254, 0.3);
            border-radius: 999px;
            padding: 8px 14px;
            font-size: 0.82rem;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.06);
            white-space: nowrap;
        }

        .dashboard-head-toggle:hover {
            background: rgba(255, 255, 255, 0.16);
            border-color: rgba(224, 241, 255, 0.58);
        }

        .control-card {
            border: 1px solid #d8e6f3;
            border-radius: 14px;
            background: #f6fbff;
            padding: 10px 12px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(30, 66, 104, 0.08);
        }

        .section-card {
            border: 1px solid #dbe7f2;
            border-radius: 14px;
            background: #ffffff;
            padding: 14px;
            margin-top: 6px;
            margin-bottom: 8px;
            box-shadow: 0 6px 16px rgba(24, 59, 94, 0.08);
        }

        .kpi-tag {
            display: inline-block;
            font-size: 0.75rem;
            letter-spacing: 0.04em;
            color: #4f6e8f;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 2px;
        }

        .book-tab-rail {
            position: fixed;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 3000;
            width: 66px;
            padding: 10px 8px;
            border-radius: 22px;
            border: 1px solid #c7daee;
            background: linear-gradient(180deg, #e9f3fd 0%, #deebf8 100%);
            box-shadow: 0 10px 24px rgba(45, 102, 156, 0.14);
            transition: width 0.2s ease;
            overflow: hidden;
        }

        .book-tab-rail:hover {
            width: 290px;
        }

        .book-tab-link {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            margin: 8px 0;
            height: 46px;
            border-radius: 14px;
            border: 1px solid #c6d9ec;
            background: #ffffff;
            box-shadow: 0 3px 10px rgba(30, 66, 104, 0.09);
            color: #2d5f8f;
            font-weight: 700;
            padding: 0 14px;
            white-space: nowrap;
        }

        .book-tab-link:hover {
            border-color: #6fb2e7;
            transform: translateY(-1px);
        }

        .book-tab-link.is-active {
            background: linear-gradient(120deg, #1086df 0%, #2a66e9 100%);
            border-color: #2a66e9;
            color: #ffffff;
            box-shadow: 0 8px 18px rgba(21, 96, 181, 0.35);
        }

        .book-tab-icon {
            display: inline-flex;
            width: 18px;
            min-width: 18px;
            justify-content: center;
            font-size: 1rem;
            line-height: 1;
        }

        .book-tab-label {
            opacity: 0;
            transition: opacity 0.18s ease;
            pointer-events: none;
        }

        .book-tab-rail:hover .book-tab-label {
            opacity: 1;
        }

        @media (max-width: 900px) {
            [data-testid="stSidebar"] {
                width: 76px !important;
                min-width: 76px !important;
                max-width: 76px !important;
            }

            [data-testid="stSidebar"] > div:first-child {
                width: 76px !important;
                min-width: 76px !important;
                max-width: 76px !important;
            }

            .stApp [data-testid="stAppViewContainer"] .main .block-container {
                padding-left: 1rem;
                padding-top: 6.4rem;
            }

            .book-tab-rail,
            .book-tab-rail:hover {
                width: 58px;
                left: 8px;
            }

            .book-tab-link {
                justify-content: center;
                padding: 0;
            }

            .book-tab-label,
            .book-tab-rail:hover .book-tab-label {
                opacity: 0;
                width: 0;
            }

            .dashboard-head {
                left: 8px;
                right: 8px;
                padding: 10px 12px;
            }

            .dashboard-head-title {
                font-size: 1.05rem;
            }

            .dashboard-head-meta {
                font-size: 0.72rem;
            }

            .dashboard-head-toggle {
                font-size: 0.72rem;
                padding: 6px 10px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
                f'<a class="book-tab-link{active_class}" href="?tab={tab_key}">'
                f'<span class="book-tab-icon">{tab_meta["icon"]}</span>'
                f'<span class="book-tab-label">{tab_meta["label"]}</span>'
                "</a>"
            )
        )

    st.markdown(
        "<div class='book-tab-rail'>" + "".join(item_blocks) + "</div>",
        unsafe_allow_html=True,
    )


def _render_fixed_header(active_tab: str, colorblind_mode: bool) -> None:
    target_state = "0" if colorblind_mode else "1"
    toggle_label = "CHE DO MU MAU: BAT" if colorblind_mode else "CHE DO MU MAU: TAT"
    toggle_href = f"?tab={active_tab}&cb={target_state}"

    st.markdown(
        f"""
        <div class="dashboard-head">
            <div>
                <p class="dashboard-head-meta">PlotTwist dashboard • Du lieu sach Tiki • 4 nhom phan tich chinh</p>
                <h1 class="dashboard-head-title">Phan tich cac yeu to anh huong den hieu qua ban hang sach</h1>
            </div>
            <a class="dashboard-head-toggle" href="{toggle_href}">• {toggle_label}</a>
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


def _render_top_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("<div class='control-card'>", unsafe_allow_html=True)

    col_scope, col_group, col_year = st.columns([1.5, 2.2, 1.4])
    with col_scope:
        scope = st.radio("Phạm vi", options=["Toàn shop", "Theo danh mục"], horizontal=True)

    with col_group:
        if scope == "Theo danh mục" and "cat_level_3" in df.columns:
            options = sorted(df["cat_level_3"].dropna().unique().tolist())
            selected_groups = st.multiselect("Danh mục cụ thể", options=options, default=[])
        elif "cat_level_2" in df.columns:
            options = sorted(df["cat_level_2"].dropna().unique().tolist())
            selected_groups = st.multiselect("Nhóm sách", options=options, default=[])
        else:
            selected_groups = []
            st.text_input("Nhóm sách", value="Không có cột danh mục", disabled=True)

    with col_year:
        if "publication_year" in df.columns and df["publication_year"].notna().any():
            years = pd.to_numeric(df["publication_year"], errors="coerce").dropna().astype(int)
            year_min, year_max = int(years.min()), int(years.max())
            selected_years = st.slider(
                "Khoảng năm xuất bản",
                min_value=year_min,
                max_value=year_max,
                value=(year_min, year_max),
            )
        else:
            selected_years = None
            st.text_input("Khoảng năm xuất bản", value="Không có dữ liệu", disabled=True)

    st.markdown("</div>", unsafe_allow_html=True)

    filtered = df.copy()

    if selected_groups:
        if scope == "Theo danh mục" and "cat_level_3" in filtered.columns:
            filtered = filtered[filtered["cat_level_3"].isin(selected_groups)]
        elif "cat_level_2" in filtered.columns:
            filtered = filtered[filtered["cat_level_2"].isin(selected_groups)]

    if selected_years is not None and "publication_year" in filtered.columns:
        low, high = selected_years
        years = pd.to_numeric(filtered["publication_year"], errors="coerce")
        filtered = filtered[years.between(low, high, inclusive="both")]

    return filtered


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

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown("<span class='kpi-tag'>Tổng doanh thu ước tính</span>", unsafe_allow_html=True)
        st.metric(label="", value=f"{revenue:,.0f} VND")
    with k2:
        st.markdown("<span class='kpi-tag'>Lượng bán trung bình</span>", unsafe_allow_html=True)
        st.metric(label="", value=f"{avg_sold:,.1f}")
    with k3:
        st.markdown("<span class='kpi-tag'>Điểm rating trung bình</span>", unsafe_allow_html=True)
        st.metric(label="", value=f"{avg_rating:.2f}")
    with k4:
        st.markdown("<span class='kpi-tag'>Số nhà xuất bản</span>", unsafe_allow_html=True)
        st.metric(label="", value=f"{n_publishers:,}")


def main() -> None:
    st.set_page_config(
        page_title="PlotTwist - Dashboard phân tích sách",
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_style()
    active_tab = _get_active_tab()
    colorblind_mode = _get_colorblind_mode()
    st.sidebar.markdown(" ")
    _render_floating_tab_rail(active_tab)
    _render_fixed_header(active_tab, colorblind_mode)

    try:
        raw_df = load_dataset(str(default_data_path()))
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    df = _prepare_data(raw_df)
    filtered_df = _render_top_filters(df)

    if filtered_df.empty:
        st.warning("Bộ lọc hiện tại không có dữ liệu. Hãy mở rộng phạm vi lọc để tiếp tục.")
        st.stop()

    colors = COLORBLIND_COLORS if colorblind_mode else NORMAL_COLORS
    heatmap_scale = "Viridis" if colorblind_mode else "Blues"

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _render_kpis(filtered_df)
    st.markdown("</div>", unsafe_allow_html=True)

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
