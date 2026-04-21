"""
filters.py — Sidebar filter widgets for the Book Sales Analytics Dashboard.

Renders all filter controls and returns filtered DataFrame.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters and return the filtered DataFrame."""

    st.sidebar.header("Bộ lọc", anchor=False)

    # ── Category filters ──
    with st.sidebar.expander(":material/category: Danh mục", expanded=False):
        cat2_options = sorted(df["cat_level_2"].dropna().unique().tolist())
        cat2_sel = st.multiselect(
            "Danh mục cấp 2",
            options=cat2_options,
            default=[],
            key="f_cat2",
            placeholder="Tất cả danh mục",
        )

        if cat2_sel:
            subset = df[df["cat_level_2"].isin(cat2_sel)]
        else:
            subset = df
        cat3_options = sorted(subset["cat_level_3"].dropna().unique().tolist())
        cat3_sel = st.multiselect(
            "Danh mục cấp 3",
            options=cat3_options,
            default=[],
            key="f_cat3",
            placeholder="Tất cả danh mục phụ",
        )

    # ── Author & Seller filters ──
    with st.sidebar.expander(":material/person: Tác giả & nhà bán", expanded=False):
        author_opts = sorted(df["authors"].dropna().unique().tolist())
        author_sel = st.multiselect(
            "Tác giả",
            options=author_opts,
            default=[],
            key="f_authors",
            placeholder="Tất cả tác giả",
        )

        seller_opts = sorted(df["current_seller_name"].dropna().unique().tolist())
        seller_sel = st.multiselect(
            "Nhà bán",
            options=seller_opts,
            default=[],
            key="f_sellers",
            placeholder="Tất cả nhà bán",
        )

    # ── Numeric range filters ──
    with st.sidebar.expander(":material/tune: Khoảng giá trị", expanded=True):
        price_min = int(df["price"].min())
        price_max = int(df["price"].max())
        price_range = st.slider(
            "Khoảng giá (₫)",
            min_value=price_min,
            max_value=price_max,
            value=(price_min, price_max),
            step=1000,
            key="f_price",
            format="%d",
        )

        rating_range = st.slider(
            "Khoảng đánh giá",
            min_value=0.0,
            max_value=5.0,
            value=(0.0, 5.0),
            step=0.1,
            key="f_rating",
        )

        discount_range = st.slider(
            "Khoảng giảm giá (%)",
            min_value=0,
            max_value=100,
            value=(0, 100),
            step=1,
            key="f_discount",
        )

    # ── Toggle filters ──
    freeship_only = st.sidebar.toggle(
        ":material/local_shipping: Chỉ Freeship",
        value=False,
        key="f_freeship",
    )

    # ── Apply filters ──
    mask = pd.Series(True, index=df.index)

    if cat2_sel:
        mask &= df["cat_level_2"].isin(cat2_sel)
    if cat3_sel:
        mask &= df["cat_level_3"].isin(cat3_sel)
    if author_sel:
        mask &= df["authors"].isin(author_sel)
    if seller_sel:
        mask &= df["current_seller_name"].isin(seller_sel)

    mask &= df["price"].between(price_range[0], price_range[1])
    mask &= df["rating_average"].between(rating_range[0], rating_range[1])
    mask &= df["discount_rate"].between(discount_range[0], discount_range[1])

    if freeship_only:
        mask &= df["has_freeship"] == True  # noqa: E712

    filtered = df.loc[mask].copy()

    # ── Filter summary ──
    active_count = sum([
        bool(cat2_sel), bool(cat3_sel), bool(author_sel), bool(seller_sel),
        price_range != (price_min, price_max),
        rating_range != (0.0, 5.0),
        discount_range != (0, 100),
        freeship_only,
    ])

    if active_count > 0:
        st.sidebar.caption(
            f":material/filter_list: {active_count} bộ lọc đang bật · "
            f"{len(filtered):,} / {len(df):,} cuốn sách"
        )
    else:
        st.sidebar.caption(f":material/database: {len(df):,} cuốn sách (chưa có bộ lọc)")

    return filtered
