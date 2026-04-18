from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st


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
    start = Path(__file__).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "data").exists() and (candidate / "src").exists():
            return candidate
    raise RuntimeError("Could not resolve project root from current file location.")


def _load_env_file(env_file_path: Path) -> None:
    if not env_file_path.exists():
        return

    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_env_data_path(base_dir: Path) -> Path | None:
    env_path = os.getenv("PLOTTWIST_DATA_PATH")
    if not env_path:
        return None

    candidate = Path(env_path)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate


def default_data_path() -> Path:
    root = project_root()
    src_dir = root / "src"
    _load_env_file(src_dir / ".env")

    env_override = _resolve_env_data_path(root)
    if env_override is not None:
        return env_override

    return root / "data" / "processed" / "book_dataset_clean_locked_rows_run2.csv"


def _normalize_boolean_value(value: object) -> object:
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


def normalize_dataset_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].map(_normalize_boolean_value).astype("boolean")

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "publication_date" in df.columns:
        df["publication_year"] = df["publication_date"].dt.year.astype("Int64")

    return df


@st.cache_data(show_spinner=False)
def load_dataset(data_path: str | None = None) -> pd.DataFrame:
    resolved_path = Path(data_path) if data_path else default_data_path()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {resolved_path}")

    df = pd.read_csv(resolved_path, encoding="utf-8-sig", low_memory=False)
    return normalize_dataset_types(df)
