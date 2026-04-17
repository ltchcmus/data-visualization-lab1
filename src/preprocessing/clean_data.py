from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime

import pandas as pd


LOCKED_COLUMNS_DEFAULT = [
    "id",
    "name",
    "authors",
    "publisher_vn",
    "cat_level_1",
    "cat_level_2",
    "discount_rate",
    "price",
    "list_price",
    "rating_average",
    "review_count",
    "current_seller_name",
    "has_freeship",
    "publication_date",
    "number_of_page",
]

OPTIONAL_LOCKED_COLUMNS = ["is_authentic"]

NUMERIC_COLS = [
    "price",
    "list_price",
    "discount_rate",
    "rating_average",
    "review_count",
    "all_time_quantity_sold",
    "stock",
    "number_of_page",
]

BOOL_COLS = ["has_freeship", "is_authentic", "has_return_policy"]
DATE_COLS = ["publication_date"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_input_path() -> Path:
    return project_root() / "data" / "raw" / "book_dataset.csv"


def default_output_path() -> Path:
    return project_root() / "data" / "processed" / "book_dataset_clean_locked_rows.csv"


def default_report_path() -> Path:
    return (
        project_root() / "data" / "processed" / "book_dataset_clean_locked_report.json"
    )


def default_locked_columns(include_optional_authentic: bool = False) -> list[str]:
    locked_columns = LOCKED_COLUMNS_DEFAULT.copy()
    if include_optional_authentic:
        locked_columns.extend(OPTIONAL_LOCKED_COLUMNS)
    return locked_columns


def parse_required_columns(
    required_cols: str | None,
    all_columns: list[str],
    include_optional_authentic: bool = False,
) -> list[str]:
    if not required_cols:
        parsed = default_locked_columns(include_optional_authentic)
    else:
        parsed = [col.strip() for col in required_cols.split(",") if col.strip()]
        if not parsed:
            raise ValueError("--required-cols is empty after parsing.")

    deduped = list(dict.fromkeys(parsed))

    missing = sorted(set(deduped) - set(all_columns))
    if missing:
        raise ValueError(f"Columns not found in dataset: {missing}")

    return deduped


def normalize_boolean_value(value: object) -> object:
    if pd.isna(value):
        return pd.NA

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False

    text = str(value).strip().lower()
    truthy = {"true", "1", "yes", "y", "t"}
    falsy = {"false", "0", "no", "n", "f"}

    if text in truthy:
        return True
    if text in falsy:
        return False

    return pd.NA


def safe_mode(series: pd.Series) -> object:
    valid = series.dropna()
    if valid.empty:
        return pd.NA
    modes = valid.mode(dropna=True)
    if modes.empty:
        return valid.iloc[0]
    return modes.iloc[0]


def strip_and_empty_to_na(df: pd.DataFrame) -> pd.DataFrame:
    object_cols = df.select_dtypes(include=["object"]).columns.tolist()
    if not object_cols:
        return df

    for col in object_cols:
        df[col] = df[col].astype("string").str.strip()

    df[object_cols] = df[object_cols].replace(r"^\s*$", pd.NA, regex=True)
    return df


def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].map(normalize_boolean_value).astype("boolean")

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def apply_basic_consistency_rules(df: pd.DataFrame) -> pd.DataFrame:
    non_negative_cols = [
        "price",
        "list_price",
        "discount_rate",
        "rating_average",
        "review_count",
        "all_time_quantity_sold",
        "stock",
        "number_of_page",
    ]

    for col in non_negative_cols:
        if col in df.columns:
            df.loc[df[col] < 0, col] = pd.NA

    if "rating_average" in df.columns:
        df.loc[
            (df["rating_average"] > 5) | (df["rating_average"] < 0), "rating_average"
        ] = pd.NA

    if "discount_rate" in df.columns:
        df.loc[
            (df["discount_rate"] > 100) | (df["discount_rate"] < 0), "discount_rate"
        ] = pd.NA

    return df


def fill_categorical_with_group_mode(
    df: pd.DataFrame,
    target_col: str,
    group_keys: list[str],
    fallback_value: str = "Unknown",
    max_groups: int = 20000,
) -> int:
    if target_col not in df.columns:
        return 0

    missing_before = int(df[target_col].isna().sum())

    for key in group_keys:
        if key not in df.columns or key == target_col:
            continue

        source = df.loc[df[target_col].notna() & df[key].notna(), [key, target_col]]
        if source.empty:
            continue

        # Skip excessively high-cardinality keys to avoid slow group-by mode.
        unique_groups = int(source[key].nunique(dropna=True))
        if unique_groups > max_groups:
            continue

        # Faster per-group mode extraction via frequency table.
        freq = (
            source.groupby([key, target_col], dropna=False)
            .size()
            .reset_index(name="_freq")
            .sort_values(by=[key, "_freq"], ascending=[True, False], kind="mergesort")
        )
        mode_map = freq.drop_duplicates(subset=[key], keep="first").set_index(key)[
            target_col
        ]

        mask = df[target_col].isna() & df[key].notna()
        if mask.any():
            df.loc[mask, target_col] = df.loc[mask, key].map(mode_map)

    if df[target_col].isna().any():
        global_mode = safe_mode(df[target_col])
        if pd.isna(global_mode):
            global_mode = fallback_value
        df[target_col] = df[target_col].fillna(global_mode)

    missing_after = int(df[target_col].isna().sum())
    return missing_before - missing_after


def fill_numeric_with_group_median(
    df: pd.DataFrame,
    target_col: str,
    group_keys: list[str],
    fallback_value: float | None = None,
) -> int:
    if target_col not in df.columns:
        return 0

    missing_before = int(df[target_col].isna().sum())

    for key in group_keys:
        if key not in df.columns or key == target_col:
            continue

        source = df.loc[df[target_col].notna() & df[key].notna(), [key, target_col]]
        if source.empty:
            continue

        median_map = source.groupby(key)[target_col].median()
        mask = df[target_col].isna() & df[key].notna()
        if mask.any():
            df.loc[mask, target_col] = df.loc[mask, key].map(median_map)

    if df[target_col].isna().any():
        global_median = df[target_col].median(skipna=True)
        if pd.isna(global_median):
            global_median = fallback_value if fallback_value is not None else 0.0
        df[target_col] = df[target_col].fillna(float(global_median))

    missing_after = int(df[target_col].isna().sum())
    return missing_before - missing_after


def fill_boolean_with_group_mode(
    df: pd.DataFrame,
    target_col: str,
    group_keys: list[str],
    fallback_value: bool = False,
) -> int:
    if target_col not in df.columns:
        return 0

    missing_before = int(df[target_col].isna().sum())

    for key in group_keys:
        if key not in df.columns or key == target_col:
            continue

        source = df.loc[df[target_col].notna() & df[key].notna(), [key, target_col]]
        if source.empty:
            continue

        mode_map = source.groupby(key)[target_col].agg(safe_mode)
        mask = df[target_col].isna() & df[key].notna()
        if mask.any():
            df.loc[mask, target_col] = df.loc[mask, key].map(mode_map)

    if df[target_col].isna().any():
        global_mode = safe_mode(df[target_col])
        if pd.isna(global_mode):
            global_mode = fallback_value
        df[target_col] = df[target_col].fillna(bool(global_mode))

    df[target_col] = df[target_col].astype("boolean")
    missing_after = int(df[target_col].isna().sum())
    return missing_before - missing_after


def fill_datetime_with_group_median(
    df: pd.DataFrame,
    target_col: str,
    group_keys: list[str],
    fallback_value: pd.Timestamp | None = None,
) -> int:
    if target_col not in df.columns:
        return 0

    missing_before = int(df[target_col].isna().sum())

    for key in group_keys:
        if key not in df.columns or key == target_col:
            continue

        source = df.loc[df[target_col].notna() & df[key].notna(), [key, target_col]]
        if source.empty:
            continue

        median_map = source.groupby(key)[target_col].median()
        mask = df[target_col].isna() & df[key].notna()
        if mask.any():
            df.loc[mask, target_col] = df.loc[mask, key].map(median_map)

    if df[target_col].isna().any():
        global_median = df[target_col].median()
        if pd.isna(global_median):
            global_median = (
                fallback_value
                if fallback_value is not None
                else pd.Timestamp("2020-01-01")
            )
        df[target_col] = df[target_col].fillna(global_median)

    missing_after = int(df[target_col].isna().sum())
    return missing_before - missing_after


def reconcile_price_triplet(df: pd.DataFrame) -> dict[str, int]:
    actions: dict[str, int] = {
        "price_from_list_discount": 0,
        "list_from_price_discount": 0,
        "discount_from_price_list": 0,
        "list_price_aligned_to_price": 0,
    }

    required = {"price", "list_price", "discount_rate"}
    if not required.issubset(df.columns):
        return actions

    mask_price = (
        df["price"].isna() & df["list_price"].notna() & df["discount_rate"].notna()
    )
    actions["price_from_list_discount"] = int(mask_price.sum())
    if mask_price.any():
        df.loc[mask_price, "price"] = df.loc[mask_price, "list_price"] * (
            1 - df.loc[mask_price, "discount_rate"] / 100
        )

    mask_list = (
        df["list_price"].isna()
        & df["price"].notna()
        & df["discount_rate"].notna()
        & (df["discount_rate"] < 100)
    )
    actions["list_from_price_discount"] = int(mask_list.sum())
    if mask_list.any():
        df.loc[mask_list, "list_price"] = df.loc[mask_list, "price"] / (
            1 - df.loc[mask_list, "discount_rate"] / 100
        )

    mask_discount = (
        df["discount_rate"].isna()
        & df["price"].notna()
        & df["list_price"].notna()
        & (df["list_price"] > 0)
    )
    actions["discount_from_price_list"] = int(mask_discount.sum())
    if mask_discount.any():
        calculated = (
            (1 - (df.loc[mask_discount, "price"] / df.loc[mask_discount, "list_price"]))
            * 100
        ).clip(lower=0, upper=100)
        df.loc[mask_discount, "discount_rate"] = calculated.round(0)

    mismatch = (
        df["price"].notna()
        & df["list_price"].notna()
        & (df["list_price"] < df["price"])
    )
    actions["list_price_aligned_to_price"] = int(mismatch.sum())
    if mismatch.any():
        df.loc[mismatch, "list_price"] = df.loc[mismatch, "price"]

    df["discount_rate"] = df["discount_rate"].clip(lower=0, upper=100)
    return actions


def apply_best_effort_imputation(
    df: pd.DataFrame, locked_columns: list[str]
) -> dict[str, int]:
    actions: dict[str, int] = {}

    actions.update(reconcile_price_triplet(df))

    # Keep group keys compact to improve runtime on large datasets.
    categorical_group_keys = ["cat_level_2", "cat_level_1", "current_seller_name"]
    numeric_group_keys = ["cat_level_2", "cat_level_1"]
    date_group_keys = ["cat_level_2", "cat_level_1"]
    bool_group_keys = ["current_seller_name", "cat_level_2", "cat_level_1"]

    for col in [
        "authors",
        "publisher_vn",
        "current_seller_name",
        "cat_level_1",
        "cat_level_2",
        "name",
    ]:
        if col in locked_columns and col in df.columns:
            actions[f"filled_{col}"] = fill_categorical_with_group_mode(
                df,
                target_col=col,
                group_keys=categorical_group_keys,
                fallback_value="Unknown",
            )

    if "price" in locked_columns and "price" in df.columns:
        actions["filled_price"] = fill_numeric_with_group_median(
            df,
            target_col="price",
            group_keys=numeric_group_keys,
            fallback_value=100000.0,
        )

    if "list_price" in locked_columns and "list_price" in df.columns:
        actions["filled_list_price"] = fill_numeric_with_group_median(
            df,
            target_col="list_price",
            group_keys=numeric_group_keys,
            fallback_value=100000.0,
        )

    if "discount_rate" in locked_columns and "discount_rate" in df.columns:
        actions["filled_discount_rate"] = fill_numeric_with_group_median(
            df,
            target_col="discount_rate",
            group_keys=numeric_group_keys,
            fallback_value=0.0,
        )

    if "rating_average" in locked_columns and "rating_average" in df.columns:
        actions["filled_rating_average"] = fill_numeric_with_group_median(
            df,
            target_col="rating_average",
            group_keys=numeric_group_keys,
            fallback_value=0.0,
        )

    if "review_count" in locked_columns and "review_count" in df.columns:
        actions["filled_review_count"] = fill_numeric_with_group_median(
            df,
            target_col="review_count",
            group_keys=numeric_group_keys,
            fallback_value=0.0,
        )
        df["review_count"] = df["review_count"].round(0)

    if "number_of_page" in locked_columns and "number_of_page" in df.columns:
        actions["filled_number_of_page"] = fill_numeric_with_group_median(
            df,
            target_col="number_of_page",
            group_keys=numeric_group_keys,
            fallback_value=250.0,
        )
        df["number_of_page"] = df["number_of_page"].round(0)

    if "publication_date" in locked_columns and "publication_date" in df.columns:
        actions["filled_publication_date"] = fill_datetime_with_group_median(
            df,
            target_col="publication_date",
            group_keys=date_group_keys,
            fallback_value=pd.Timestamp("2020-01-01"),
        )

    if "has_freeship" in locked_columns and "has_freeship" in df.columns:
        actions["filled_has_freeship"] = fill_boolean_with_group_mode(
            df,
            target_col="has_freeship",
            group_keys=bool_group_keys,
            fallback_value=False,
        )

    if "is_authentic" in locked_columns and "is_authentic" in df.columns:
        actions["filled_is_authentic"] = fill_boolean_with_group_mode(
            df,
            target_col="is_authentic",
            group_keys=bool_group_keys,
            fallback_value=True,
        )

    return actions


def clean_dataset(
    input_path: Path,
    output_path: Path,
    report_path: Path,
    min_rows: int,
    required_cols_arg: str | None,
    include_optional_authentic: bool,
    output_encoding: str,
) -> dict[str, object]:
    df = pd.read_csv(input_path, low_memory=False)
    raw_rows = len(df)

    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"], keep="first")
    rows_after_dedup = len(df)

    df = strip_and_empty_to_na(df)
    df = convert_types(df)
    df = apply_basic_consistency_rules(df)

    required_columns = parse_required_columns(
        required_cols_arg,
        df.columns.tolist(),
        include_optional_authentic=include_optional_authentic,
    )

    locked_missing_before = (
        df[required_columns].isna().sum().sort_values(ascending=False)
    )

    imputation_actions = apply_best_effort_imputation(df, required_columns)
    df = apply_basic_consistency_rules(df)
    reconcile_after_impute = reconcile_price_triplet(df)
    for key, value in reconcile_after_impute.items():
        imputation_actions[key] = int(imputation_actions.get(key, 0)) + int(value)

    locked_missing_after_imputation = (
        df[required_columns].isna().sum().sort_values(ascending=False)
    )

    cleaned_df = df.dropna(subset=required_columns).copy()
    cleaned_rows = len(cleaned_df)
    meets_minimum = cleaned_rows >= min_rows

    all_missing_after = df.isna().sum().sort_values(ascending=False)

    if "publication_date" in cleaned_df.columns:
        cleaned_df["publication_date"] = cleaned_df["publication_date"].dt.strftime(
            "%Y-%m-%d"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    actual_output_path = output_path
    try:
        cleaned_df.to_csv(output_path, index=False, encoding=output_encoding)
    except PermissionError:
        # Common when file is open in Excel. Fallback to a timestamped filename.
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_output_path = output_path.with_name(
            f"{output_path.stem}_{suffix}{output_path.suffix}"
        )
        cleaned_df.to_csv(fallback_output_path, index=False, encoding=output_encoding)
        actual_output_path = fallback_output_path

    report: dict[str, object] = {
        "input_path": str(input_path),
        "output_path": str(actual_output_path),
        "output_encoding": output_encoding,
        "raw_rows": int(raw_rows),
        "rows_after_dedup": int(rows_after_dedup),
        "rows_after_locked_filter": int(cleaned_rows),
        "locked_feature_count": int(len(required_columns)),
        "locked_features": required_columns,
        "minimum_required_rows": int(min_rows),
        "meets_minimum_rows": bool(meets_minimum),
        "dropped_rows_due_to_remaining_locked_missing": int(
            rows_after_dedup - cleaned_rows
        ),
        "missing_locked_before_imputation": {
            str(col): int(cnt) for col, cnt in locked_missing_before.items()
        },
        "missing_locked_after_imputation": {
            str(col): int(cnt) for col, cnt in locked_missing_after_imputation.items()
        },
        "imputation_actions": {
            str(key): int(val) for key, val in imputation_actions.items()
        },
        "top_missing_all_columns_after_imputation": {
            str(col): int(cnt) for col, cnt in all_missing_after.head(10).items()
        },
        "output_columns_count": int(len(cleaned_df.columns)),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Clean ecommerce dataset with locked core columns and best-effort "
            "imputation to preserve as many rows and columns as possible."
        )
    )
    parser.add_argument(
        "--input", type=Path, default=default_input_path(), help="Input CSV path"
    )
    parser.add_argument(
        "--output", type=Path, default=default_output_path(), help="Output CSV path"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=default_report_path(),
        help="Output JSON report path",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=5000,
        help="Minimum required number of cleaned rows",
    )
    parser.add_argument(
        "--required-cols",
        type=str,
        default=None,
        help=(
            "Comma-separated locked feature names. "
            "If omitted, use the pre-agreed locked set for dashboard/EDA."
        ),
    )
    parser.add_argument(
        "--include-optional-authentic",
        action="store_true",
        help="Also lock is_authentic as mandatory (optional by default).",
    )
    parser.add_argument(
        "--output-encoding",
        type=str,
        default="utf-8-sig",
        help=(
            "Encoding used to write CSV output. "
            "Use utf-8-sig for best compatibility with Excel Vietnamese text."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    report = clean_dataset(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report,
        min_rows=args.min_rows,
        required_cols_arg=args.required_cols,
        include_optional_authentic=args.include_optional_authentic,
        output_encoding=args.output_encoding,
    )

    print("Data cleaning complete.")
    print(f"Input rows: {report['raw_rows']}")
    print(f"Rows after dedup: {report['rows_after_dedup']}")
    print(f"Rows after locked-feature filter: {report['rows_after_locked_filter']}")
    print(f"Minimum required rows: {report['minimum_required_rows']}")
    print(f"Meets minimum rows: {report['meets_minimum_rows']}")
    print(f"Saved cleaned data to: {report['output_path']}")
    print(f"Saved report to: {args.report}")


if __name__ == "__main__":
    main()
