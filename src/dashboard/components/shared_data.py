from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st


@dataclass
class DashboardDataState:
    raw_df: pd.DataFrame
    filtered_df: pd.DataFrame
    shared_df: pd.DataFrame
    filter_state: dict[str, Any]
    filter_meta: dict[str, Any]
    version: int


def _empty_state() -> DashboardDataState:
    empty = pd.DataFrame()
    return DashboardDataState(
        raw_df=empty,
        filtered_df=empty,
        shared_df=empty,
        filter_state={},
        filter_meta={},
        version=0,
    )


def _as_dataframe(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    return pd.DataFrame()


def set_dashboard_data_state(
    raw_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    shared_df: pd.DataFrame,
    filter_state: dict[str, Any],
    filter_meta: dict[str, Any],
) -> None:
    st.session_state["raw_df"] = raw_df
    st.session_state["filtered_df"] = filtered_df
    st.session_state["shared_df"] = shared_df
    st.session_state["filter_state"] = filter_state
    st.session_state["filter_meta"] = filter_meta
    st.session_state["shared_data_version"] = (
        int(st.session_state.get("shared_data_version", 0)) + 1
    )


def get_dashboard_data_state(load_if_missing: bool = True) -> DashboardDataState:
    raw_df = _as_dataframe(st.session_state.get("raw_df"))
    filtered_df = _as_dataframe(st.session_state.get("filtered_df"))
    shared_df = _as_dataframe(st.session_state.get("shared_df"))

    if load_if_missing and raw_df.empty:
        from .data_loader import default_data_path, load_dataset

        try:
            raw_df = load_dataset(str(default_data_path()))
        except FileNotFoundError:
            pass

    if filtered_df.empty and not raw_df.empty:
        filtered_df = raw_df

    if shared_df.empty and not filtered_df.empty:
        shared_df = filtered_df

    if raw_df.empty and filtered_df.empty and shared_df.empty:
        return _empty_state()

    return DashboardDataState(
        raw_df=raw_df,
        filtered_df=filtered_df,
        shared_df=shared_df,
        filter_state=st.session_state.get("filter_state", {}),
        filter_meta=st.session_state.get("filter_meta", {}),
        version=int(st.session_state.get("shared_data_version", 0)),
    )


def get_shared_df(load_if_missing: bool = True) -> pd.DataFrame:
    return get_dashboard_data_state(load_if_missing=load_if_missing).shared_df


def get_filtered_df(load_if_missing: bool = True) -> pd.DataFrame:
    return get_dashboard_data_state(load_if_missing=load_if_missing).filtered_df


def get_filter_meta() -> dict[str, Any]:
    return dict(st.session_state.get("filter_meta", {}))
