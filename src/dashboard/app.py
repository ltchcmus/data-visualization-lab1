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
        @import url("https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&display=swap");

        :root {
            --pri-900: #102844;
            --pri-800: #173a5e;
            --pri-700: #1f4f7d;
            --pri-500: #0ea5e9;
            --acc-500: #f59e0b;
            --bg-050: #f5f9fc;
            --ink-700: #334155;
            --ink-500: #64748b;
            --line-200: #dbe7f2;
            --left-sidebar-width: 100px;
            --content-left-gap: 14px;
        }

        html, body, [class*="css"] {
            font-family: "Be Vietnam Pro", "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif !important;
        }

        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
        }

        /* Collapse the space Streamlit reserves for the hidden native header */
        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
        }

        .stApp {
            background: linear-gradient(180deg, #eff5fb 0%, #f8fbff 60%, #eef3f9 100%);
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
            padding-top: 3.8rem;
        }

        /* ── HEADER ── */
        .dashboard-head {
            position: fixed;
            top: 4px;
            left: calc(var(--left-sidebar-width) + var(--content-left-gap));
            right: 14px;
            z-index: 1001;
            border-radius: 10px;
            background: var(--pri-800);
            color: #ecf6ff;
            box-shadow: 0 4px 12px rgba(15, 47, 83, 0.22);
            border: 1px solid rgba(187, 216, 244, 0.15);
            display: grid;
            grid-template-columns: 1fr auto;
            align-items: center;
            gap: 16px;
            padding: 10px 20px;
        }

        .hdr-left {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .hdr-logo {
            width: 38px;
            height: 38px;
            background: rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
            font-size: 1.15rem;
            line-height: 1;
        }

        .hdr-school {
            font-size: 0.6rem;
            color: #93afc9;
            line-height: 1.5;
            white-space: nowrap;
        }

        .hdr-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.3;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .hdr-right {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-shrink: 0;
        }

        .hdr-stat {
            text-align: right;
        }

        .hdr-stat-val {
            font-size: 1.05rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1;
        }

        .hdr-stat-lbl {
            font-size: 0.58rem;
            color: #7da4c0;
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .hdr-badge {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            padding: 6px 12px;
            text-align: center;
            text-decoration: none;
            display: block;
            transition: background 0.2s ease;
        }

        .hdr-badge:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .hdr-badge-val {
            font-size: 1rem;
            line-height: 1;
        }

        .hdr-badge-lbl {
            font-size: 0.55rem;
            color: #93afc9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
            white-space: nowrap;
        }

        /* ── KPI STRIP ── */
        .kpi-strip {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 12px;
        }

        .kpi-box {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-top: 3px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 14px;
        }

        .kpi-box.accent-blue  { border-top-color: #2563eb; }
        .kpi-box.accent-amber { border-top-color: #f59e0b; }
        .kpi-box.accent-red   { border-top-color: #ea580c; }
        .kpi-box.accent-slate { border-top-color: #0ea5e9; }

        .kpi-lbl {
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            color: #64748b;
            margin-bottom: 5px;
        }

        .kpi-val {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e293b;
            line-height: 1;
        }

        .kpi-val .u {
            font-size: 0.68rem;
            font-weight: 400;
            color: #64748b;
        }

        /* ── SECTION CARDS ── */
        .section-card {
            border: 1px solid #dbe7f2;
            border-radius: 14px;
            background: #ffffff;
            padding: 14px;
            margin-top: 6px;
            margin-bottom: 8px;
            box-shadow: 0 6px 16px rgba(24, 59, 94, 0.08);
        }

        /* ── FILTER BAR ── */
        .control-card {
            border: 1px solid #d8e6f3;
            border-radius: 12px;
            background: #ffffff;
            padding: 10px 16px 6px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(30, 66, 104, 0.07);
        }

        /* widget labels */
        .control-card .stRadio > label,
        .control-card .stMultiSelect > label,
        .control-card .stSelectbox > label {
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: var(--ink-500) !important;
        }

        /* radio as pill buttons */
        .control-card .stRadio [data-baseweb="radio"] {
            padding: 3px 10px 3px 4px;
            border-radius: 6px;
            border: 1px solid #dbe7f2;
            background: #f1f5f9;
            margin-right: 4px;
            transition: background 0.15s;
        }

        .control-card .stRadio [data-baseweb="radio"]:has(input:checked) {
            background: var(--pri-800);
            border-color: var(--pri-800);
        }

        .control-card .stRadio [data-baseweb="radio"]:has(input:checked) span {
            color: #ffffff !important;
        }

        .control-card .stRadio [data-baseweb="radio"] span:last-child {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--ink-700);
        }

        /* multiselect light */
        .control-card .stMultiSelect [data-baseweb="select"] {
            background: #f8fafc !important;
            border: 1px solid #d8e6f3 !important;
            border-radius: 8px !important;
        }

        .control-card .stMultiSelect [data-baseweb="select"]:focus-within {
            border-color: var(--pri-500) !important;
            box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.15) !important;
        }

        .control-card .stMultiSelect [data-baseweb="tag"] {
            background: #eff6ff !important;
            border: 1px solid #bfdbfe !important;
            border-radius: 4px !important;
        }

        .control-card .stMultiSelect [data-baseweb="tag"] span {
            color: #1d4ed8 !important;
            font-size: 0.74rem !important;
        }

        /* selectbox (year drill-out) */
        .control-card .stSelectbox [data-baseweb="select"] {
            background: #f8fafc !important;
            border: 1px solid #d8e6f3 !important;
            border-radius: 8px !important;
        }

        .control-card .stSelectbox [data-baseweb="select"]:focus-within {
            border-color: var(--pri-500) !important;
            box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.15) !important;
        }

        /* ── FLOATING TAB RAIL ── */
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

        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

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
                padding-top: 3rem;
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
                padding: 8px 12px;
            }

            .hdr-title { font-size: 0.78rem; }

            .kpi-strip {
                grid-template-columns: repeat(2, 1fr);
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
                <a class="hdr-badge" href="{toggle_href}">
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


_BOOK_TYPE_MAP: dict[str, str | None] = {
    "Tất cả": None,
    "Sách tiếng Việt": "sach-truyen-tieng-viet",
    "Sách tiếng Anh": "sach-tieng-anh",
}

_YEAR_PRESET_MAP: dict[str, tuple[int, int] | None] = {
    "Tất cả năm": None,
    "2020 – nay": (2020, 9999),
    "2015 – 2019": (2015, 2019),
    "2010 – 2014": (2010, 2014),
    "Trước 2010": (0, 2009),
}


def _render_top_filters(df: pd.DataFrame) -> pd.DataFrame:
    col_lang, col_genre, col_year = st.columns([1.8, 2.5, 1.3])

    with col_lang:
        lang_label = st.radio(
            "Loại sách",
            options=list(_BOOK_TYPE_MAP.keys()),
            horizontal=True,
        )

    lang_val = _BOOK_TYPE_MAP[lang_label]
    if lang_val is not None and "cat_level_2" in df.columns:
        lang_filtered = df[df["cat_level_2"] == lang_val]
    else:
        lang_filtered = df

    with col_genre:
        if "cat_level_3" in lang_filtered.columns:
            genre_options = sorted(lang_filtered["cat_level_3"].dropna().unique().tolist())
        else:
            genre_options = []
        selected_genres = st.multiselect("Thể loại", options=genre_options, default=[])

    with col_year:
        year_label = st.selectbox(
            "Năm xuất bản",
            options=list(_YEAR_PRESET_MAP.keys()),
        )

    filtered = lang_filtered.copy()

    if selected_genres and "cat_level_3" in filtered.columns:
        filtered = filtered[filtered["cat_level_3"].isin(selected_genres)]

    year_range = _YEAR_PRESET_MAP[year_label]
    if year_range is not None and "publication_year" in filtered.columns:
        low, high = year_range
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
    filtered_df = _render_top_filters(df)

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
