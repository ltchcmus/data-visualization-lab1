from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ..components.shared_data import get_dashboard_data_state


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _render_metric_cards(df: pd.DataFrame) -> None:
    rows = int(len(df))

    avg_price = None
    if "price" in df.columns:
        s = _safe_numeric(df["price"]).dropna()
        if not s.empty:
            avg_price = float(s.mean())

    avg_rating = None
    if "rating_average" in df.columns:
        s = _safe_numeric(df["rating_average"]).dropna()
        if not s.empty:
            avg_rating = float(s.mean())

    total_reviews = None
    if "review_count" in df.columns:
        s = _safe_numeric(df["review_count"]).dropna()
        if not s.empty:
            total_reviews = float(s.sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filtered books", f"{rows:,}")
    c2.metric("Average price", f"{avg_price:,.0f}" if avg_price is not None else "N/A")
    c3.metric(
        "Average rating", f"{avg_rating:.2f}" if avg_rating is not None else "N/A"
    )
    c4.metric(
        "Total reviews", f"{total_reviews:,.0f}" if total_reviews is not None else "N/A"
    )


def _render_top_category_chart(df: pd.DataFrame) -> None:
    if "cat_level_1" not in df.columns:
        st.info("Column cat_level_1 is not available for category chart.")
        return

    category = df["cat_level_1"].fillna("<NA>").value_counts().head(10)
    chart_df = category.rename_axis("category").reset_index(name="book_count")

    fig = px.bar(
        chart_df,
        x="book_count",
        y="category",
        orientation="h",
        title="Top categories after filter",
        color="book_count",
        color_continuous_scale="Teal",
    )
    fig.update_layout(
        height=380, coloraxis_showscale=False, margin=dict(l=10, r=10, t=50, b=10)
    )
    fig.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig, use_container_width=True)


def _render_price_chart(df: pd.DataFrame) -> None:
    if "price" not in df.columns:
        st.info("Column price is not available for distribution chart.")
        return

    s = _safe_numeric(df["price"]).dropna()
    if s.empty:
        st.info("No valid numeric price values to plot.")
        return

    plot_df = pd.DataFrame({"price": s})
    fig = px.histogram(
        plot_df,
        x="price",
        nbins=40,
        title="Price distribution after filter",
        color_discrete_sequence=["#0f766e"],
    )
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _render_top_seller_table(df: pd.DataFrame) -> None:
    if "current_seller_name" not in df.columns:
        st.info("Column current_seller_name is not available for seller table.")
        return

    sellers = (
        df["current_seller_name"]
        .fillna("<NA>")
        .value_counts()
        .head(12)
        .rename_axis("seller")
        .reset_index(name="book_count")
    )
    sellers["share_%"] = (sellers["book_count"] / len(df) * 100).round(2)
    st.dataframe(sellers, use_container_width=True, hide_index=True)


def render_sample_dashboard_page() -> None:
    state = get_dashboard_data_state(load_if_missing=False)
    filtered_df = state.filtered_df
    shared_df = state.shared_df
    filter_meta = state.filter_meta

    st.markdown("## Sample Dashboard Page")
    st.caption(
        "This page is a ready-to-use example for your teammate. "
        "All charts below automatically use current global filter output."
    )

    if filtered_df.empty:
        st.warning(
            "No data available for dashboard rendering with current filter state."
        )
        return

    _render_metric_cards(filtered_df)

    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        _render_top_category_chart(filtered_df)
    with chart_col_2:
        _render_price_chart(filtered_df)

    table_col_1, table_col_2 = st.columns([1.3, 1.7])
    with table_col_1:
        st.markdown("### Top Sellers")
        _render_top_seller_table(filtered_df)

    with table_col_2:
        st.markdown("### Current Filter Meta")
        st.write(f"- Active filters: {filter_meta.get('active_filter_count', 0)}")
        st.write(
            f"- Rows after filter: {filter_meta.get('row_after', len(filtered_df)):,}"
        )
        st.write(
            f"- Shared columns: {filter_meta.get('selected_columns_count', len(shared_df.columns))}"
        )
        st.write(f"- State version: {state.version}")
        with st.expander("Preview shared_df (first 30 rows)", expanded=False):
            st.dataframe(shared_df.head(30), use_container_width=True)
