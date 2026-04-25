from __future__ import annotations

from typing import Any

import pandas as pd

from .contracts import JsonDict


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _clean_text_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def dataset_overview(
    df: pd.DataFrame, *, focus_cols: list[str] | None = None
) -> JsonDict:
    if df.empty:
        return {
            "row_count": 0,
            "column_count": int(df.shape[1]),
            "missing_by_column": {},
            "notes": ["No data after filtering."],
        }

    working_cols = focus_cols if focus_cols else df.columns.tolist()
    working_cols = [col for col in working_cols if col in df.columns]
    sub = df[working_cols] if working_cols else df

    missing = (
        sub.isna()
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .mul(100)
        .round(2)
        .to_dict()
    )

    return {
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "missing_by_column_pct_top10": missing,
    }


def make_univariate_numeric_builder(
    *,
    column: str,
    quantiles: tuple[float, ...] = (0.1, 0.25, 0.5, 0.75, 0.9),
) -> Any:
    def _builder(df: pd.DataFrame, filter_context: JsonDict | None = None) -> JsonDict:
        if column not in df.columns:
            return {
                "column": column,
                "error": f"Missing column: {column}",
                "filter_context": filter_context or {},
            }

        series = _to_numeric(df[column]).dropna()
        if series.empty:
            return {
                "column": column,
                "row_count": int(len(df)),
                "valid_count": 0,
                "filter_context": filter_context or {},
                "notes": [f"Column {column} has no valid numeric values."],
            }

        q_map = {
            f"q_{int(q * 100)}": round(float(series.quantile(q)), 4) for q in quantiles
        }

        return {
            "column": column,
            "row_count": int(len(df)),
            "valid_count": int(series.shape[0]),
            "mean": round(float(series.mean()), 4),
            "median": round(float(series.median()), 4),
            "std": round(float(series.std(ddof=0)), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "quantiles": q_map,
            "filter_context": filter_context or {},
        }

    return _builder


def make_group_aggregate_builder(
    *,
    group_col: str,
    value_col: str,
    agg: str = "mean",
    top_n: int = 8,
    min_count: int = 1,
    ascending: bool = False,
) -> Any:
    allowed_agg = {"mean", "median", "sum", "count"}
    if agg not in allowed_agg:
        raise ValueError(f"agg must be one of {sorted(allowed_agg)}")

    def _builder(df: pd.DataFrame, filter_context: JsonDict | None = None) -> JsonDict:
        missing = [col for col in (group_col, value_col) if col not in df.columns]
        if missing:
            return {
                "group_col": group_col,
                "value_col": value_col,
                "error": f"Missing columns: {', '.join(missing)}",
                "filter_context": filter_context or {},
            }

        local = df[[group_col, value_col]].copy()
        local[group_col] = _clean_text_series(local[group_col])
        local[value_col] = _to_numeric(local[value_col])
        local = local.dropna(subset=[group_col, value_col])

        if local.empty:
            return {
                "group_col": group_col,
                "value_col": value_col,
                "row_count": int(len(df)),
                "valid_count": 0,
                "filter_context": filter_context or {},
                "notes": ["No valid rows after cleaning group/value columns."],
            }

        grouped = local.groupby(group_col)[value_col]
        if agg == "count":
            metric = grouped.count()
        elif agg == "sum":
            metric = grouped.sum()
        elif agg == "median":
            metric = grouped.median()
        else:
            metric = grouped.mean()

        counts = grouped.count()
        stats_df = pd.DataFrame({"metric": metric, "count": counts})
        # Avoid DataFrame.query scope issues for closure vars in some runtimes.
        stats_df = stats_df[stats_df["count"] >= int(min_count)]
        stats_df = stats_df.sort_values("metric", ascending=ascending)

        top = stats_df.head(top_n).reset_index()
        top_rows = [
            {
                "group": str(row[group_col]),
                "metric": round(float(row["metric"]), 4),
                "count": int(row["count"]),
            }
            for _, row in top.iterrows()
        ]

        return {
            "group_col": group_col,
            "value_col": value_col,
            "agg": agg,
            "row_count": int(len(df)),
            "valid_count": int(local.shape[0]),
            "group_count": int(stats_df.shape[0]),
            "top_groups": top_rows,
            "filter_context": filter_context or {},
        }

    return _builder


def make_correlation_builder(*, columns: list[str], method: str = "pearson") -> Any:
    def _builder(df: pd.DataFrame, filter_context: JsonDict | None = None) -> JsonDict:
        available = [col for col in columns if col in df.columns]
        if len(available) < 2:
            return {
                "columns": columns,
                "error": "Need at least two available columns for correlation.",
                "filter_context": filter_context or {},
            }

        numeric = df[available].apply(pd.to_numeric, errors="coerce")
        corr = numeric.corr(method=method).round(4)

        pairs: list[JsonDict] = []
        for i, col_a in enumerate(corr.columns):
            for col_b in corr.columns[i + 1 :]:
                value = corr.loc[col_a, col_b]
                if pd.isna(value):
                    continue
                pairs.append(
                    {
                        "pair": f"{col_a}__{col_b}",
                        "corr": float(value),
                    }
                )

        pairs.sort(key=lambda row: abs(row["corr"]), reverse=True)

        return {
            "columns": available,
            "method": method,
            "pair_count": int(len(pairs)),
            "top_pairs": pairs[:10],
            "filter_context": filter_context or {},
        }

    return _builder


def build_evidence_packet(
    chart_metadata: JsonDict,
    chart_evidence: JsonDict,
    *,
    extra_context: JsonDict | None = None,
) -> JsonDict:
    payload = {
        "chart": chart_metadata,
        "evidence": chart_evidence,
    }
    if extra_context:
        payload["context"] = extra_context
    return payload
