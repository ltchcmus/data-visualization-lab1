from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .filter_engine import BOOK_TYPE_MAP, YEAR_PRESET_MAP, apply_top_filters


WIDGET_KEYS = {
    "selected_columns": "global_selected_columns",
    "cat_level_1": "global_cat_level_1",
    "authors": "global_authors",
    "publisher_vn": "global_publisher_vn",
    "current_seller_name": "global_current_seller_name",
    "publication_year": "global_publication_year",
    "discount_rate": "global_discount_rate",
    "rating_average": "global_rating_average",
    "number_of_page": "global_number_of_page",
    "has_freeship": "global_has_freeship",
}

SEARCH_KEYS = {
    "authors": "global_authors_search",
    "publisher_vn": "global_publisher_search",
    "current_seller_name": "global_seller_search",
}


def _clone_default(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return tuple(value)
    return value


def initialize_filter_widgets(defaults: dict[str, Any]) -> None:
    for state_key, widget_key in WIDGET_KEYS.items():
        if widget_key not in st.session_state:
            st.session_state[widget_key] = _clone_default(defaults[state_key])

    for search_key in SEARCH_KEYS.values():
        if search_key not in st.session_state:
            st.session_state[search_key] = ""


def reset_filter_widgets(defaults: dict[str, Any]) -> None:
    for state_key, widget_key in WIDGET_KEYS.items():
        st.session_state[widget_key] = _clone_default(defaults[state_key])

    for search_key in SEARCH_KEYS.values():
        st.session_state[search_key] = ""


def _merge_selected_options(options: list[Any], selected: list[Any]) -> list[Any]:
    merged = list(options)
    for value in selected:
        if value not in merged:
            merged.append(value)
    return merged


def _top_options_with_search(
    df: pd.DataFrame,
    col: str,
    search_text: str,
    max_options: int,
) -> tuple[list[Any], int, int]:
    if col not in df.columns:
        return [], 0, 0

    values = df[col].dropna()
    if values.empty:
        return [], 0, 0

    if search_text.strip():
        search = search_text.strip().lower()
        values = values[values.astype(str).str.lower().str.contains(search, na=False)]

    counts = values.value_counts(dropna=True)
    options = counts.index.tolist()
    total_available = len(options)
    if total_available > max_options:
        options = options[:max_options]

    return options, total_available, len(options)


def _render_numeric_range_slider(
    ui: Any,
    label: str,
    key: str,
    bounds: tuple[float, float],
    is_integer: bool = False,
    step: float | int = 1,
) -> None:
    low_bound, high_bound = bounds

    if is_integer:
        min_value = int(round(low_bound))
        max_value = int(round(high_bound))
        current = st.session_state.get(key, (min_value, max_value))
        current_low = int(round(current[0]))
        current_high = int(round(current[1]))
        current_low = max(min_value, min(current_low, max_value))
        current_high = max(min_value, min(current_high, max_value))
        if current_low > current_high:
            current_low, current_high = current_high, current_low

        st.session_state[key] = (current_low, current_high)

        if min_value == max_value:
            ui.caption(f"{label}: {min_value} (fixed)")
            return

        ui.slider(
            label,
            min_value=min_value,
            max_value=max_value,
            value=(current_low, current_high),
            key=key,
            step=int(step),
        )
        return

    min_value = float(low_bound)
    max_value = float(high_bound)
    current = st.session_state.get(key, (min_value, max_value))
    current_low = float(current[0])
    current_high = float(current[1])
    current_low = max(min_value, min(current_low, max_value))
    current_high = max(min_value, min(current_high, max_value))
    if current_low > current_high:
        current_low, current_high = current_high, current_low

    st.session_state[key] = (current_low, current_high)

    if abs(min_value - max_value) < 1e-9:
        ui.caption(f"{label}: {min_value:g} (fixed)")
        return

    ui.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=(current_low, current_high),
        key=key,
        step=float(step),
    )


def render_filter_panel(df: pd.DataFrame, defaults: dict[str, Any]) -> None:
    st.markdown(
        """
        <style>
        .filter-card {
            border: 1px solid #cfe0f2;
            border-radius: 16px;
            padding: 14px 18px;
            background: linear-gradient(105deg, #dcedff 0%, #eff6ff 52%, #ffffff 100%);
            margin-bottom: 12px;
            box-shadow: 0 8px 18px rgba(31, 79, 125, 0.12);
        }
        .filter-title {
            font-size: 1.05rem;
            font-weight: 650;
            color: #1f3653;
            margin-bottom: 2px;
        }
        .filter-subtitle {
            color: #47617d;
            font-size: 0.92rem;
            margin-bottom: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="filter-card">
            <div class="filter-title">Global Filter Workspace</div>
            <p class="filter-subtitle">Filter controls are grouped to keep the page clean. Use advanced popovers for large lists.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    quick_col_1, quick_col_2, quick_col_3 = st.columns([1.6, 1.4, 1.0])

    with quick_col_1:
        if "cat_level_1" in df.columns:
            cat_level_1_options = sorted(df["cat_level_1"].dropna().unique().tolist())
            st.multiselect(
                "Category level 1",
                options=cat_level_1_options,
                key=WIDGET_KEYS["cat_level_1"],
                placeholder="All categories",
            )

    with quick_col_2:
        if "publication_year" in df.columns:
            year_options = sorted(
                df["publication_year"].dropna().astype(int).unique().tolist(),
                reverse=True,
            )
            year_options = _merge_selected_options(
                year_options,
                st.session_state[WIDGET_KEYS["publication_year"]],
            )
            st.multiselect(
                "Publication year",
                options=year_options,
                key=WIDGET_KEYS["publication_year"],
                placeholder="All years",
            )

    with quick_col_3:
        st.selectbox(
            "Has freeship",
            options=["all", "true", "false"],
            format_func=lambda value: {
                "all": "All",
                "true": "Only True",
                "false": "Only False",
            }[value],
            key=WIDGET_KEYS["has_freeship"],
        )

    range_col_1, range_col_2, range_col_3 = st.columns(3)
    with range_col_1:
        _render_numeric_range_slider(
            st,
            "Discount rate",
            WIDGET_KEYS["discount_rate"],
            bounds=tuple(float(v) for v in defaults["discount_rate"]),
            is_integer=False,
            step=1.0,
        )
    with range_col_2:
        _render_numeric_range_slider(
            st,
            "Rating average",
            WIDGET_KEYS["rating_average"],
            bounds=tuple(float(v) for v in defaults["rating_average"]),
            is_integer=False,
            step=0.1,
        )
    with range_col_3:
        _render_numeric_range_slider(
            st,
            "Number of pages",
            WIDGET_KEYS["number_of_page"],
            bounds=tuple(float(v) for v in defaults["number_of_page"]),
            is_integer=True,
            step=1,
        )

    advanced_col_1, advanced_col_2, advanced_col_3 = st.columns(3)

    with advanced_col_1:
        with st.popover("Authors filter"):
            st.text_input(
                "Search authors",
                key=SEARCH_KEYS["authors"],
                placeholder="Type to narrow author list",
            )
            author_options, author_total, shown_count = _top_options_with_search(
                df,
                "authors",
                st.session_state[SEARCH_KEYS["authors"]],
                max_options=300,
            )
            author_options = _merge_selected_options(
                author_options,
                st.session_state[WIDGET_KEYS["authors"]],
            )
            st.multiselect(
                "Authors",
                options=author_options,
                key=WIDGET_KEYS["authors"],
                placeholder="All authors",
            )
            if author_total > shown_count:
                st.caption(
                    f"Showing top {shown_count} from {author_total} matches. Refine search to narrow results."
                )

    with advanced_col_2:
        with st.popover("Publisher filter"):
            st.text_input(
                "Search publisher",
                key=SEARCH_KEYS["publisher_vn"],
                placeholder="Type to narrow publisher list",
            )
            publisher_options, publisher_total, shown_count = _top_options_with_search(
                df,
                "publisher_vn",
                st.session_state[SEARCH_KEYS["publisher_vn"]],
                max_options=300,
            )
            publisher_options = _merge_selected_options(
                publisher_options,
                st.session_state[WIDGET_KEYS["publisher_vn"]],
            )
            st.multiselect(
                "Publisher",
                options=publisher_options,
                key=WIDGET_KEYS["publisher_vn"],
                placeholder="All publishers",
            )
            if publisher_total > shown_count:
                st.caption(
                    f"Showing top {shown_count} from {publisher_total} matches. Refine search to narrow results."
                )

    with advanced_col_3:
        with st.popover("Seller filter"):
            st.text_input(
                "Search seller",
                key=SEARCH_KEYS["current_seller_name"],
                placeholder="Type to narrow seller list",
            )
            seller_options, seller_total, shown_count = _top_options_with_search(
                df,
                "current_seller_name",
                st.session_state[SEARCH_KEYS["current_seller_name"]],
                max_options=300,
            )
            seller_options = _merge_selected_options(
                seller_options,
                st.session_state[WIDGET_KEYS["current_seller_name"]],
            )
            st.multiselect(
                "Current seller",
                options=seller_options,
                key=WIDGET_KEYS["current_seller_name"],
                placeholder="All sellers",
            )
            if seller_total > shown_count:
                st.caption(
                    f"Showing top {shown_count} from {seller_total} matches. Refine search to narrow results."
                )

    with st.expander("Column selection for shared dataset", expanded=False):
        st.multiselect(
            "Choose columns to share with dashboard tabs",
            options=df.columns.tolist(),
            key=WIDGET_KEYS["selected_columns"],
            help="Selected columns are kept in shared_df and CSV export.",
        )


def render_filter_sidebar(df: pd.DataFrame) -> None:
    # Backward-compatible alias if older code still calls this function.
    defaults = st.session_state.get("filter_defaults", {})
    render_filter_panel(df, defaults)


def collect_filter_state_from_widgets() -> dict[str, Any]:
    return {
        "selected_columns": list(st.session_state[WIDGET_KEYS["selected_columns"]]),
        "cat_level_1": list(st.session_state[WIDGET_KEYS["cat_level_1"]]),
        "authors": list(st.session_state[WIDGET_KEYS["authors"]]),
        "publisher_vn": list(st.session_state[WIDGET_KEYS["publisher_vn"]]),
        "current_seller_name": list(
            st.session_state[WIDGET_KEYS["current_seller_name"]]
        ),
        "publication_year": [
            int(year)
            for year in st.session_state[WIDGET_KEYS["publication_year"]]
            if pd.notna(year)
        ],
        "discount_rate": tuple(
            float(v) for v in st.session_state[WIDGET_KEYS["discount_rate"]]
        ),
        "rating_average": tuple(
            float(v) for v in st.session_state[WIDGET_KEYS["rating_average"]]
        ),
        "number_of_page": tuple(
            float(v) for v in st.session_state[WIDGET_KEYS["number_of_page"]]
        ),
        "has_freeship": st.session_state[WIDGET_KEYS["has_freeship"]],
    }


def render_top_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.markdown(
        """
        <style>
        .filter-toggle-wrap {
            margin: 2px 0 8px 0;
        }
        .st-key-filter_toggle_shell {
            margin-top: 8px !important;
            margin-bottom: 12px !important;
            border-radius: 14px;
            border: 1px solid #7ea2c9;
            background: linear-gradient(110deg, #e9f2ff 0%, #d6e8ff 48%, #edf6ff 100%);
            box-shadow: 0 12px 24px rgba(30, 64, 175, 0.18);
            padding: 10px 14px;
        }
        .st-key-filter_toggle_shell [data-testid="stHorizontalBlock"] {
            align-items: center !important;
            min-height: 40px;
        }
        .filter-toggle-title {
            color: #153458 !important;
            font-weight: 800;
            font-size: 1.12rem !important;
            letter-spacing: 0.015em;
            line-height: 1.25;
            padding-left: 6px;
        }
        .st-key-filter_toggle_shell .st-key-global_filter_panel_open {
            margin: 0 !important;
            display: flex;
            justify-content: flex-end;
        }
        .st-key-filter_toggle_shell .st-key-global_filter_panel_open [data-testid="stToggle"] {
            margin: 0 !important;
        }
        .st-key-filter_toggle_shell .st-key-global_filter_panel_open [data-baseweb="checkbox"] {
            transform: scale(1.12);
            transform-origin: right center;
        }
        .top-filter-title {
            display: none !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] {
            background: #ffffff !important;
            border: 1px solid #d8e6f3 !important;
            border-radius: 10px !important;
            box-shadow: 0 5px 14px rgba(9, 18, 34, 0.06) !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] * {
            background-color: transparent !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] > div,
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] > div > div {
            background: #ffffff !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] span,
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] div,
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] input {
            color: #1E293B !important;
            -webkit-text-fill-color: #1E293B !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] input::placeholder {
            color: #64748B !important;
            -webkit-text-fill-color: #64748B !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="tag"] {
            background: #F8FAFC !important;
            border: 1px solid #d6e3f0 !important;
            border-radius: 10px !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="tag"] span {
            color: #1E293B !important;
        }
        [data-testid="column"]:has(.top-filter-title) [data-baseweb="select"] svg {
            color: #64748B !important;
            fill: #64748B !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "global_filter_panel_open" not in st.session_state:
        st.session_state["global_filter_panel_open"] = False
    if "global_lang_label" not in st.session_state:
        st.session_state["global_lang_label"] = list(BOOK_TYPE_MAP.keys())[0]
    if "global_selected_genres" not in st.session_state:
        st.session_state["global_selected_genres"] = []
    if "global_year_label" not in st.session_state:
        st.session_state["global_year_label"] = list(YEAR_PRESET_MAP.keys())[0]

    rating_values = pd.to_numeric(df.get("rating_average"), errors="coerce").dropna().clip(lower=0, upper=5)
    rating_default = (0.0, 5.0)
    if not rating_values.empty:
        rating_default = (float(rating_values.min()), float(rating_values.max()))

    if "global_rating_range" not in st.session_state:
        st.session_state["global_rating_range"] = rating_default
    if "global_freeship_filter" not in st.session_state:
        st.session_state["global_freeship_filter"] = ["Có Freeship", "Không Freeship"]

    with st.container(key="filter_toggle_shell"):
        t_col1, t_col2 = st.columns([8.2, 1.4], vertical_alignment="center")
        with t_col1:
            st.markdown("<div class='filter-toggle-title'>Bộ lọc Dashboard</div>", unsafe_allow_html=True)
        with t_col2:
            st.toggle(
                "Bật/tắt bộ lọc",
                key="global_filter_panel_open",
                label_visibility="collapsed",
                help="Bật để hiện toàn bộ bộ lọc dashboard.",
            )

    if st.session_state["global_filter_panel_open"]:
        col_lang, col_genre, col_year = st.columns([1.8, 2.5, 1.3])

        with col_lang:
            st.markdown("<div class='top-filter-title'>Loại sách</div>", unsafe_allow_html=True)
            st.selectbox(
                "Loại sách",
                options=list(BOOK_TYPE_MAP.keys()),
                key="global_lang_label",
                label_visibility="collapsed",
            )

        lang_val_ui = BOOK_TYPE_MAP.get(st.session_state["global_lang_label"])
        if lang_val_ui is not None and "cat_level_2" in df.columns:
            genre_df = df[df["cat_level_2"] == lang_val_ui]
        else:
            genre_df = df

        with col_genre:
            st.markdown("<div class='top-filter-title'>Thể loại</div>", unsafe_allow_html=True)
            if "cat_level_3" in genre_df.columns:
                genre_options = sorted(genre_df["cat_level_3"].dropna().unique().tolist())
            else:
                genre_options = []
            st.multiselect(
                "Thể loại",
                options=genre_options,
                key="global_selected_genres",
                label_visibility="collapsed",
                placeholder="Thể loại",
            )

        with col_year:
            st.markdown("<div class='top-filter-title'>Năm xuất bản</div>", unsafe_allow_html=True)
            st.selectbox(
                "Năm xuất bản",
                options=list(YEAR_PRESET_MAP.keys()),
                key="global_year_label",
                label_visibility="collapsed",
            )

        adv_col_1, adv_col_2 = st.columns([2.0, 1.2])
        with adv_col_1:
            st.slider(
                "Khoảng rating",
                min_value=0.0,
                max_value=5.0,
                value=st.session_state["global_rating_range"],
                step=0.1,
                key="global_rating_range",
                help="Áp dụng cho toàn bộ dashboard.",
            )
        with adv_col_2:
            st.multiselect(
                "Trạng thái freeship",
                options=["Có Freeship", "Không Freeship"],
                default=["Có Freeship", "Không Freeship"],
                key="global_freeship_filter",
                help="Có thể chọn một hoặc cả hai trạng thái.",
            )

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    selected_freeship_labels = st.session_state.get("global_freeship_filter", ["Có Freeship", "Không Freeship"])
    freeship_options: list[bool] = []
    if "Có Freeship" in selected_freeship_labels:
        freeship_options.append(True)
    if "Không Freeship" in selected_freeship_labels:
        freeship_options.append(False)

    return apply_top_filters(
        df,
        lang_label=st.session_state["global_lang_label"],
        selected_genres=list(st.session_state.get("global_selected_genres", [])),
        year_label=st.session_state["global_year_label"],
        rating_range=tuple(float(v) for v in st.session_state["global_rating_range"]),
        freeship_options=freeship_options,
    )
