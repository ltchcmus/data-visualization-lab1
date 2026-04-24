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
        min_val, max_val = int(round(low_bound)), int(round(high_bound))
        current = st.session_state.get(key, (min_val, max_val))
        lo = max(min_val, min(int(round(current[0])), max_val))
        hi = max(min_val, min(int(round(current[1])), max_val))
        if lo > hi:
            lo, hi = hi, lo
        st.session_state[key] = (lo, hi)
        if min_val == max_val:
            ui.caption(f"{label}: {min_val} (fixed)")
            return
        ui.slider(label, min_value=min_val, max_value=max_val, value=(lo, hi), key=key, step=int(step))
    else:
        min_val, max_val = float(low_bound), float(high_bound)
        current = st.session_state.get(key, (min_val, max_val))
        lo = max(min_val, min(float(current[0]), max_val))
        hi = max(min_val, min(float(current[1]), max_val))
        if lo > hi:
            lo, hi = hi, lo
        st.session_state[key] = (lo, hi)
        if abs(min_val - max_val) < 1e-9:
            ui.caption(f"{label}: {min_val:g} (fixed)")
            return
        ui.slider(label, min_value=min_val, max_value=max_val, value=(lo, hi), key=key, step=float(step))


def _render_popover_filter(
    df: pd.DataFrame,
    popover_label: str,
    col: str,
    search_key: str,
    widget_key: str,
    search_placeholder: str,
    multiselect_label: str,
    multiselect_placeholder: str,
) -> None:
    with st.popover(popover_label):
        st.text_input(f"Search {multiselect_label.lower()}", key=search_key, placeholder=search_placeholder)
        options, total, shown = _top_options_with_search(
            df, col, st.session_state[search_key], max_options=300
        )
        options = _merge_selected_options(options, st.session_state[widget_key])
        st.multiselect(multiselect_label, options=options, key=widget_key, placeholder=multiselect_placeholder)
        if total > shown:
            st.caption(f"Showing top {shown} from {total} matches. Refine search to narrow results.")


def render_filter_panel(df: pd.DataFrame, defaults: dict[str, Any]) -> None:
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
            st.multiselect(
                "Category level 1",
                options=sorted(df["cat_level_1"].dropna().unique().tolist()),
                key=WIDGET_KEYS["cat_level_1"],
                placeholder="All categories",
            )
    with quick_col_2:
        if "publication_year" in df.columns:
            year_options = sorted(
                df["publication_year"].dropna().astype(int).unique().tolist(), reverse=True
            )
            year_options = _merge_selected_options(year_options, st.session_state[WIDGET_KEYS["publication_year"]])
            st.multiselect("Publication year", options=year_options, key=WIDGET_KEYS["publication_year"], placeholder="All years")
    with quick_col_3:
        st.selectbox(
            "Has freeship",
            options=["all", "true", "false"],
            format_func=lambda v: {"all": "All", "true": "Only True", "false": "Only False"}[v],
            key=WIDGET_KEYS["has_freeship"],
        )

    range_col_1, range_col_2, range_col_3 = st.columns(3)
    with range_col_1:
        _render_numeric_range_slider(st, "Discount rate", WIDGET_KEYS["discount_rate"],
                                     bounds=tuple(float(v) for v in defaults["discount_rate"]), step=1.0)
    with range_col_2:
        _render_numeric_range_slider(st, "Rating average", WIDGET_KEYS["rating_average"],
                                     bounds=tuple(float(v) for v in defaults["rating_average"]), step=0.1)
    with range_col_3:
        _render_numeric_range_slider(st, "Number of pages", WIDGET_KEYS["number_of_page"],
                                     bounds=tuple(float(v) for v in defaults["number_of_page"]),
                                     is_integer=True, step=1)

    adv_col_1, adv_col_2, adv_col_3 = st.columns(3)
    with adv_col_1:
        _render_popover_filter(df, "Authors filter", "authors",
                               SEARCH_KEYS["authors"], WIDGET_KEYS["authors"],
                               "Type to narrow author list", "Authors", "All authors")
    with adv_col_2:
        _render_popover_filter(df, "Publisher filter", "publisher_vn",
                               SEARCH_KEYS["publisher_vn"], WIDGET_KEYS["publisher_vn"],
                               "Type to narrow publisher list", "Publisher", "All publishers")
    with adv_col_3:
        _render_popover_filter(df, "Seller filter", "current_seller_name",
                               SEARCH_KEYS["current_seller_name"], WIDGET_KEYS["current_seller_name"],
                               "Type to narrow seller list", "Current seller", "All sellers")

    with st.expander("Column selection for shared dataset", expanded=False):
        st.multiselect(
            "Choose columns to share with dashboard tabs",
            options=df.columns.tolist(),
            key=WIDGET_KEYS["selected_columns"],
            help="Selected columns are kept in shared_df and CSV export.",
        )


def render_filter_sidebar(df: pd.DataFrame) -> None:
    defaults = st.session_state.get("filter_defaults", {})
    render_filter_panel(df, defaults)


def collect_filter_state_from_widgets() -> dict[str, Any]:
    return {
        "selected_columns": list(st.session_state[WIDGET_KEYS["selected_columns"]]),
        "cat_level_1": list(st.session_state[WIDGET_KEYS["cat_level_1"]]),
        "authors": list(st.session_state[WIDGET_KEYS["authors"]]),
        "publisher_vn": list(st.session_state[WIDGET_KEYS["publisher_vn"]]),
        "current_seller_name": list(st.session_state[WIDGET_KEYS["current_seller_name"]]),
        "publication_year": [
            int(year) for year in st.session_state[WIDGET_KEYS["publication_year"]] if pd.notna(year)
        ],
        "discount_rate": tuple(float(v) for v in st.session_state[WIDGET_KEYS["discount_rate"]]),
        "rating_average": tuple(float(v) for v in st.session_state[WIDGET_KEYS["rating_average"]]),
        "number_of_page": tuple(float(v) for v in st.session_state[WIDGET_KEYS["number_of_page"]]),
        "has_freeship": st.session_state[WIDGET_KEYS["has_freeship"]],
    }


def _init_top_filter_state(df: pd.DataFrame) -> None:
    defaults: list[tuple[str, Any]] = [
        ("global_filter_panel_open", False),
        ("global_lang_label", list(BOOK_TYPE_MAP.keys())[0]),
        ("global_selected_genres", []),
        ("global_year_label", list(YEAR_PRESET_MAP.keys())[0]),
        ("global_freeship_filter", ["Có Freeship", "Không Freeship"]),
    ]
    for key, default in defaults:
        if key not in st.session_state:
            st.session_state[key] = default

    if "global_rating_range" not in st.session_state:
        rating_values = pd.to_numeric(df.get("rating_average"), errors="coerce").dropna().clip(lower=0, upper=5)
        rating_default = (float(rating_values.min()), float(rating_values.max())) if not rating_values.empty else (0.0, 5.0)
        st.session_state["global_rating_range"] = rating_default


def _build_genre_df(df: pd.DataFrame) -> pd.DataFrame:
    lang_val = BOOK_TYPE_MAP.get(st.session_state["global_lang_label"])
    if lang_val is not None and "cat_level_2" in df.columns:
        return df[df["cat_level_2"] == lang_val]
    return df


def _collect_freeship_options() -> list[bool]:
    selected = st.session_state.get("global_freeship_filter", ["Có Freeship", "Không Freeship"])
    options: list[bool] = []
    if "Có Freeship" in selected:
        options.append(True)
    if "Không Freeship" in selected:
        options.append(False)
    return options


def render_top_filters(df: pd.DataFrame) -> pd.DataFrame:
    _init_top_filter_state(df)

    with st.container(key="filter_toggle_shell"):
        t_col1, t_col2 = st.columns([8.2, 1.4], vertical_alignment="center")
        with t_col1:
            st.markdown("<div class='filter-toggle-title'>Bộ lọc Dashboard</div>", unsafe_allow_html=True)
        with t_col2:
            st.toggle("Bật/tắt bộ lọc", key="global_filter_panel_open",
                      label_visibility="collapsed", help="Bật để hiện toàn bộ bộ lọc dashboard.")

    if st.session_state["global_filter_panel_open"]:
        col_lang, col_genre, col_year = st.columns([1.8, 2.5, 1.3])

        with col_lang:
            st.markdown("<div class='top-filter-title'>Loại sách</div>", unsafe_allow_html=True)
            st.selectbox("Loại sách", options=list(BOOK_TYPE_MAP.keys()),
                         key="global_lang_label", label_visibility="collapsed")

        genre_df = _build_genre_df(df)
        genre_options = sorted(genre_df["cat_level_3"].dropna().unique().tolist()) if "cat_level_3" in genre_df.columns else []

        with col_genre:
            st.markdown("<div class='top-filter-title'>Thể loại</div>", unsafe_allow_html=True)
            st.multiselect("Thể loại", options=genre_options, key="global_selected_genres",
                           label_visibility="collapsed", placeholder="Thể loại")

        with col_year:
            st.markdown("<div class='top-filter-title'>Năm xuất bản</div>", unsafe_allow_html=True)
            st.selectbox("Năm xuất bản", options=list(YEAR_PRESET_MAP.keys()),
                         key="global_year_label", label_visibility="collapsed")

        adv_col_1, adv_col_2 = st.columns([2.0, 1.2])
        with adv_col_1:
            st.slider("Khoảng rating", min_value=0.0, max_value=5.0,
                      value=st.session_state["global_rating_range"], step=0.1,
                      key="global_rating_range", help="Áp dụng cho toàn bộ dashboard.")
        with adv_col_2:
            st.multiselect("Trạng thái freeship", options=["Có Freeship", "Không Freeship"],
                           default=["Có Freeship", "Không Freeship"], key="global_freeship_filter",
                           help="Có thể chọn một hoặc cả hai trạng thái.")

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    return apply_top_filters(
        df,
        lang_label=st.session_state["global_lang_label"],
        selected_genres=list(st.session_state.get("global_selected_genres", [])),
        year_label=st.session_state["global_year_label"],
        rating_range=tuple(float(v) for v in st.session_state["global_rating_range"]),
        freeship_options=_collect_freeship_options(),
    )
