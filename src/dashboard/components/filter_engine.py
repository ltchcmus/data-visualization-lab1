from __future__ import annotations

from typing import Any

import pandas as pd


LIST_FILTER_COLS = [
    "cat_level_1",
    "authors",
    "publisher_vn",
    "current_seller_name",
    "publication_year",
]

RANGE_FILTER_COLS = ["discount_rate", "rating_average", "number_of_page"]
BOOL_FILTER_COL = "has_freeship"


def _numeric_bounds(df: pd.DataFrame, col: str, as_int: bool = False) -> tuple[float, float]:
    if col not in df.columns:
        return (0.0, 0.0)

    values = pd.to_numeric(df[col], errors="coerce").dropna()
    if values.empty:
        return (0.0, 0.0)

    low = float(values.min())
    high = float(values.max())
    if as_int:
        return (float(int(low)), float(int(high)))
    return (low, high)


def build_filter_defaults(df: pd.DataFrame) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "selected_columns": df.columns.tolist(),
        "cat_level_1": [],
        "authors": [],
        "publisher_vn": [],
        "current_seller_name": [],
        "publication_year": [],
        "discount_rate": _numeric_bounds(df, "discount_rate"),
        "rating_average": _numeric_bounds(df, "rating_average"),
        "number_of_page": _numeric_bounds(df, "number_of_page", as_int=True),
        "has_freeship": "all",
    }
    return defaults


def _sanitize_multi_value(
    values: Any,
    valid_values: list[Any],
) -> list[Any]:
    if not isinstance(values, list):
        return []

    valid_set = set(valid_values)
    return [value for value in values if value in valid_set]


def _sanitize_range_value(
    value: Any,
    default_bounds: tuple[float, float],
) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default_bounds

    try:
        low = float(value[0])
        high = float(value[1])
    except (TypeError, ValueError):
        return default_bounds

    if low > high:
        low, high = high, low

    default_low, default_high = default_bounds
    low = max(default_low, min(low, default_high))
    high = min(default_high, max(high, default_low))

    return (low, high)


def sanitize_filter_state(
    df: pd.DataFrame,
    filter_state: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    valid_columns = df.columns.tolist()
    cleaned["selected_columns"] = _sanitize_multi_value(
        filter_state.get("selected_columns", defaults["selected_columns"]),
        valid_columns,
    )
    if not cleaned["selected_columns"]:
        cleaned["selected_columns"] = defaults["selected_columns"]

    for col in LIST_FILTER_COLS:
        if col in df.columns:
            valid_values = df[col].dropna().tolist()
            cleaned[col] = _sanitize_multi_value(filter_state.get(col, []), valid_values)
        else:
            cleaned[col] = []

    for col in RANGE_FILTER_COLS:
        cleaned[col] = _sanitize_range_value(
            filter_state.get(col, defaults[col]),
            defaults[col],
        )

    has_freeship = str(filter_state.get("has_freeship", defaults["has_freeship"]))
    if has_freeship not in {"all", "true", "false"}:
        has_freeship = "all"
    cleaned["has_freeship"] = has_freeship

    return cleaned


def _has_non_default_range(
    selected_range: tuple[float, float],
    default_range: tuple[float, float],
) -> bool:
    return (
        abs(selected_range[0] - default_range[0]) > 1e-9
        or abs(selected_range[1] - default_range[1]) > 1e-9
    )


def apply_filters(
    df: pd.DataFrame,
    filter_state: dict[str, Any],
    defaults: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    mask = pd.Series(True, index=df.index)
    active_filters: list[str] = []

    for col in ["cat_level_1", "authors", "publisher_vn", "current_seller_name"]:
        values = filter_state.get(col, [])
        if values and col in df.columns:
            mask &= df[col].isin(values)
            active_filters.append(f"{col}: {len(values)} selected")

    publication_years = filter_state.get("publication_year", [])
    if publication_years and "publication_year" in df.columns:
        mask &= df["publication_year"].isin(publication_years)
        active_filters.append(f"publication_year: {len(publication_years)} selected")

    for col in RANGE_FILTER_COLS:
        if col in df.columns:
            low, high = filter_state[col]
            numeric_series = pd.to_numeric(df[col], errors="coerce")
            mask &= numeric_series.between(low, high, inclusive="both")

            if _has_non_default_range((low, high), defaults[col]):
                active_filters.append(f"{col}: {low:g} to {high:g}")

    if "has_freeship" in df.columns:
        freeship_mode = filter_state.get("has_freeship", "all")
        if freeship_mode in {"true", "false"}:
            target = freeship_mode == "true"
            match = (df["has_freeship"].astype("boolean") == target).fillna(False)
            mask &= match
            active_filters.append(f"has_freeship: {target}")

    filtered_rows_df = df.loc[mask].copy()

    selected_columns = [
        col for col in filter_state.get("selected_columns", df.columns.tolist()) if col in filtered_rows_df.columns
    ]
    if not selected_columns:
        selected_columns = filtered_rows_df.columns.tolist()

    shared_df = filtered_rows_df[selected_columns].copy()

    row_before = int(len(df))
    row_after = int(len(filtered_rows_df))
    retention_pct = (row_after / row_before * 100) if row_before else 0.0

    meta = {
        "row_before": row_before,
        "row_after": row_after,
        "retention_pct": round(retention_pct, 3),
        "active_filters": active_filters,
        "active_filter_count": len(active_filters),
        "selected_columns": selected_columns,
        "selected_columns_count": len(selected_columns),
    }

    return filtered_rows_df, shared_df, meta
