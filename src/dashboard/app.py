from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

if __package__ in {None, ""}:
    # Allow running this file directly: python app.py from src/dashboard.
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from dashboard.components.data_loader import default_data_path, load_dataset
    from dashboard.components.filter_engine import (
        apply_filters,
        build_filter_defaults,
        sanitize_filter_state,
    )
    from dashboard.components.filter_ui import (
        collect_filter_state_from_widgets,
        initialize_filter_widgets,
        render_filter_panel,
        reset_filter_widgets,
    )
else:
    from .components.data_loader import default_data_path, load_dataset
    from .components.filter_engine import (
        apply_filters,
        build_filter_defaults,
        sanitize_filter_state,
    )
    from .components.filter_ui import (
        collect_filter_state_from_widgets,
        initialize_filter_widgets,
        render_filter_panel,
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
        "This page manages global filter state and shared dataset for the main dashboard."
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

    action_col_1, action_col_2, _ = st.columns([1.2, 1.2, 6])
    with action_col_1:
        if st.button("Reset all filters", use_container_width=True):
            reset_filter_widgets(defaults)
            st.session_state["filter_state"] = _clone_state(defaults)
            st.rerun()

    with action_col_2:
        st.download_button(
            label="Export filtered CSV",
            data=_prepare_csv_bytes(st.session_state.get("shared_df", raw_df)),
            file_name="book_dataset_filtered_scope.csv",
            mime="text/csv",
            use_container_width=True,
        )

    render_filter_panel(raw_df, defaults)

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

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Rows before filter", f"{filter_meta['row_before']:,}")
    col_b.metric("Rows after filter", f"{filter_meta['row_after']:,}")
    col_c.metric("Retained", f"{filter_meta['retention_pct']:.2f}%")
    col_d.metric("Active filters", f"{filter_meta['active_filter_count']}")

    st.caption(
        f"Selected columns for shared dataset: {filter_meta['selected_columns_count']}"
    )

    if filter_meta["active_filter_count"] == 0:
        st.info("No active row filters. Shared dataset currently contains all rows.")
    else:
        st.markdown("### Active Filters")
        for active_filter in filter_meta["active_filters"]:
            st.write(f"- {active_filter}")

    st.success(
        "Global filter state is ready. Your teammate dashboard can read shared_df from session state."
    )

    with st.expander("Debug preview (optional)", expanded=False):
        if shared_df.empty:
            st.warning("Current filters returned no rows. Adjust filters to continue.")
        else:
            st.dataframe(shared_df.head(50), use_container_width=True)


if __name__ == "__main__":
    main()
