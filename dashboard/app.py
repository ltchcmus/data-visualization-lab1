from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.components.data_loader import default_data_path, load_dataset
from dashboard.components.filter_engine import (
    apply_filters,
    build_filter_defaults,
    sanitize_filter_state,
)
from dashboard.components.filter_ui import (
    collect_filter_state_from_widgets,
    initialize_filter_widgets,
    render_filter_sidebar,
    reset_filter_widgets,
)


def _clone_state(data: dict[str, Any]) -> dict[str, Any]:
    cloned: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list):
            cloned[key] = list(value)
        elif isinstance(value, tuple):
            cloned[key] = tuple(value)
        else:
            cloned[key] = value
    return cloned


def _prepare_csv_bytes(df) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def main() -> None:
    st.set_page_config(
        page_title="PlotTwist - Global Select and Filter",
        layout="wide",
    )

    st.title("Global Data Scope")
    st.caption(
        "Use this global frame to select columns and filter rows. "
        "The resulting dataset is shared for downstream visualization tabs."
    )

    data_path = default_data_path()
    try:
        raw_df = load_dataset(str(data_path))
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    defaults = build_filter_defaults(raw_df)
    st.session_state["filter_defaults"] = _clone_state(defaults)

    initialize_filter_widgets(defaults)

    if st.sidebar.button("Reset all filters", use_container_width=True):
        reset_filter_widgets(defaults)
        st.session_state["filter_state"] = _clone_state(defaults)
        st.rerun()

    render_filter_sidebar(raw_df)

    user_filter_state = collect_filter_state_from_widgets()
    cleaned_filter_state = sanitize_filter_state(raw_df, user_filter_state, defaults)

    filtered_rows_df, shared_df, filter_meta = apply_filters(
        raw_df,
        cleaned_filter_state,
        defaults,
    )

    st.session_state["raw_df"] = raw_df
    st.session_state["filtered_df"] = filtered_rows_df
    st.session_state["shared_df"] = shared_df
    st.session_state["filter_state"] = cleaned_filter_state
    st.session_state["filter_meta"] = filter_meta

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Rows before filter", f"{filter_meta['row_before']:,}")
    col_b.metric("Rows after filter", f"{filter_meta['row_after']:,}")
    col_c.metric("Retained", f"{filter_meta['retention_pct']:.2f}%")

    st.write(
        f"Selected columns for shared dataset: {filter_meta['selected_columns_count']}"
    )

    if filter_meta["active_filter_count"] == 0:
        st.info("No active row filters. Shared dataset currently contains all rows.")
    else:
        st.markdown("### Active Filters")
        for active_filter in filter_meta["active_filters"]:
            st.write(f"- {active_filter}")

    st.download_button(
        label="Download filtered dataset CSV",
        data=_prepare_csv_bytes(shared_df),
        file_name="book_dataset_filtered_scope.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("### Shared Dataset Preview")
    st.caption(
        "This is the dataset after global select and filter. "
        "Future tabs can reuse it from session state key shared_df."
    )

    if shared_df.empty:
        st.warning("Current filters returned no rows. Adjust filters to continue.")
    else:
        st.dataframe(shared_df.head(300), use_container_width=True)

    with st.expander("Session State Contract", expanded=False):
        st.write("raw_df: full dataset loaded from processed CSV")
        st.write("filtered_df: row-filtered dataset with all columns")
        st.write("shared_df: selected columns after row filtering")
        st.write("filter_state: current global select and filter settings")
        st.write("filter_meta: row counts, retention, active filters, selected columns")


if __name__ == "__main__":
    main()
