from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

FREE_TRUE_LABEL = "Có Freeship"
FREE_FALSE_LABEL = "Không Freeship"


def _resolve_seller_column(df: pd.DataFrame) -> str | None:
    for col in ["current_seller", "current_seller_name"]:
        if col in df.columns:
            return col
    return None


def _to_bool(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.lower()
    mapped = normalized.map(
        {
            "true": True,
            "1": True,
            "yes": True,
            "y": True,
            "co": True,
            "có": True,
            "false": False,
            "0": False,
            "no": False,
            "n": False,
            "khong": False,
            "không": False,
        }
    )
    return mapped


def _freeship_label(series: pd.Series) -> pd.Series:
    return series.map({True: FREE_TRUE_LABEL, False: FREE_FALSE_LABEL})


def _format_chart(fig, *, height: int = 380, x_grid: bool = False, y_grid: bool = True) -> None:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin={"l": 14, "r": 14, "t": 58, "b": 14},
        font={"color": "#0f172a"},
        title={"font": {"size": 16, "color": "#0f172a"}},
        legend={"orientation": "h", "y": 1.1, "x": 1.0, "xanchor": "right", "yanchor": "bottom"},
    )
    fig.update_xaxes(showgrid=x_grid, gridcolor="#e2e8f0", zeroline=False)
    fig.update_yaxes(showgrid=y_grid, gridcolor="#e2e8f0", zeroline=False)


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["rating_average"] = pd.to_numeric(work.get("rating_average"), errors="coerce")
    work["review_count"] = pd.to_numeric(work.get("review_count"), errors="coerce")
    work["all_time_quantity_sold"] = pd.to_numeric(work.get("all_time_quantity_sold"), errors="coerce")
    work["has_freeship"] = _to_bool(work.get("has_freeship", pd.Series(dtype=object)))

    seller_col = _resolve_seller_column(work)
    if seller_col is None:
        work["seller_name"] = "Không rõ"
    else:
        work["seller_name"] = work[seller_col].astype("string").str.strip().fillna("Không rõ")
        work.loc[work["seller_name"].isin(["", "<NA>"]), "seller_name"] = "Không rõ"

    return work


def _render_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, tuple[float, float], list[str]]:
    st.markdown("<div class='tab4-filter-card'>", unsafe_allow_html=True)
    c0, c1, c2 = st.columns([1.25, 1.7, 1.15])

    with c0:
        st.markdown("<div class='tab4-filter-title'>Bộ lọc tương tác</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='tab4-filter-sub'>Lọc nhanh theo rating và chính sách freeship để so sánh hành vi doanh số.</div>",
            unsafe_allow_html=True,
        )

    rating_valid = df["rating_average"].dropna().clip(lower=0, upper=5)
    default_range = (0.0, 5.0)
    if not rating_valid.empty:
        default_range = (float(rating_valid.min()), float(rating_valid.max()))

    with c1:
        rating_range = st.slider(
            "Lọc theo khoảng rating",
            min_value=0.0,
            max_value=5.0,
            value=default_range,
            step=0.1,
            key="tab4_rating_range",
        )

    with c2:
        freeship_choice = st.multiselect(
            "Lọc theo freeship",
            options=[FREE_TRUE_LABEL, FREE_FALSE_LABEL],
            default=[FREE_TRUE_LABEL, FREE_FALSE_LABEL],
            key="tab4_freeship_options",
        )

    filtered = df[df["rating_average"].between(rating_range[0], rating_range[1], inclusive="both")].copy()

    if freeship_choice:
        allowed = []
        if FREE_TRUE_LABEL in freeship_choice:
            allowed.append(True)
        if FREE_FALSE_LABEL in freeship_choice:
            allowed.append(False)
        filtered = filtered[filtered["has_freeship"].isin(allowed)]
    else:
        filtered = filtered.iloc[0:0]

    with c0:
        st.metric("Bản ghi sau lọc", f"{len(filtered):,}")

    st.markdown("</div>", unsafe_allow_html=True)

    return filtered, rating_range, freeship_choice


def _chart_11_scatter(df: pd.DataFrame, colors: list[str]):
    data = df[(df["rating_average"].notna()) & (df["review_count"] > 0) & (df["all_time_quantity_sold"] > 0)].copy()
    if data.empty:
        return None

    data["review_count_log10"] = np.log10(data["review_count"])

    x_min = float(data["rating_average"].min())
    x_max = float(data["rating_average"].max())
    x_pad = 0.06
    x_range = [max(0.0, x_min - x_pad), min(5.0, x_max + x_pad)]

    fig = px.density_heatmap(
        data,
        x="rating_average",
        y="review_count_log10",
        z="all_time_quantity_sold",
        histfunc="sum",
        nbinsx=34,
        nbinsy=26,
        color_continuous_scale="Blues",
        hover_data={
            "rating_average": ":.2f",
            "review_count": ":,.0f",
            "all_time_quantity_sold": ":,.0f",
            "seller_name": True,
            "review_count_log10": False,
        },
        labels={
            "rating_average": "Rating Average",
            "review_count_log10": "Review Count (log10)",
            "all_time_quantity_sold": "Tổng doanh số",
        },
        title="Biểu đồ 1.1: Density Heatmap Rating vs Review (log), màu theo tổng doanh số",
    )
    _format_chart(fig, height=430)

    y_tick_raw = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
    y_tick_vals = [np.log10(v) for v in y_tick_raw]
    y_min = float(data["review_count_log10"].min())
    y_max = float(data["review_count_log10"].max())
    y_ticks_in_range = [v for v in y_tick_vals if y_min - 0.08 <= v <= y_max + 0.08]
    y_tick_text = [f"{int(10 ** v):,}" for v in y_ticks_in_range]

    fig.update_layout(
        coloraxis_colorbar={"title": "Tổng doanh số"},
        bargap=0.02,
    )
    fig.update_xaxes(range=x_range, dtick=0.2)
    fig.update_yaxes(tickmode="array", tickvals=y_ticks_in_range, ticktext=y_tick_text)
    return fig


def _chart_12_rating_bin(df: pd.DataFrame, colors: list[str]):
    data = df[(df["rating_average"].notna()) & (df["all_time_quantity_sold"].notna())].copy()
    if data.empty:
        return None

    labels = ["<3", "3-4", "4-4.8", "4.8-5"]
    bins = [-0.001, 3, 4, 4.8, 5.001]
    data["rating_bin"] = pd.cut(data["rating_average"], bins=bins, labels=labels, include_lowest=True, right=True)

    agg = (
        data.groupby("rating_bin", observed=False)["all_time_quantity_sold"]
        .mean()
        .reindex(labels)
        .reset_index()
        .rename(columns={"all_time_quantity_sold": "avg_sold"})
    )

    fig = px.bar(
        agg,
        x="rating_bin",
        y="avg_sold",
        color="rating_bin",
        color_discrete_sequence=colors if colors else ["#2563eb", "#0ea5e9", "#22c55e", "#f97316"],
        hover_data={"avg_sold": ":,.0f"},
        labels={"rating_bin": "Nhóm rating", "avg_sold": "Doanh số trung bình"},
        title="Biểu đồ 1.2: Doanh số trung bình theo nhóm rating",
    )
    fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
    _format_chart(fig, height=340, y_grid=True)
    fig.update_layout(showlegend=False)
    return fig


def _chart_13_review_bin_line(df: pd.DataFrame, colors: list[str]):
    data = df[(df["review_count"].notna()) & (df["all_time_quantity_sold"].notna())].copy()
    if data.empty:
        return None

    labels = ["0-10", "11-50", "50-100", ">100"]
    bins = [-0.001, 10, 50, 100, float("inf")]
    data["review_bin"] = pd.cut(data["review_count"], bins=bins, labels=labels, include_lowest=True, right=True)

    agg = (
        data.groupby("review_bin", observed=False)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            total_sold=("all_time_quantity_sold", "sum"),
            book_count=("all_time_quantity_sold", "size"),
        )
        .reindex(labels)
        .reset_index()
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=agg["review_bin"],
            y=agg["avg_sold"],
            mode="lines+markers",
            line={"width": 3, "color": colors[0] if colors else "#2563eb"},
            marker={"size": 9, "color": colors[1] if len(colors) > 1 else "#f97316"},
            customdata=agg[["total_sold", "book_count"]],
            hovertemplate=(
                "Nhóm review: %{x}<br>"
                "Doanh số trung bình: %{y:,.0f}<br>"
                "Tổng doanh số: %{customdata[0]:,.0f}<br>"
                "Số đầu sách: %{customdata[1]:,.0f}<extra></extra>"
            ),
            name="Doanh số trung bình",
        )
    )
    fig.update_layout(
        title="Biểu đồ 1.3: Điểm bùng phát doanh số theo nhóm review",
        xaxis_title="Nhóm review_count",
        yaxis_title="Doanh số trung bình",
    )
    _format_chart(fig, height=340)
    return fig


def _chart_21_freeship_box(df: pd.DataFrame, colors: list[str]):
    data = df[(df["has_freeship"].notna()) & (df["all_time_quantity_sold"] > 0)].copy()
    if data.empty:
        return None

    data["freeship_label"] = _freeship_label(data["has_freeship"])
    color_map = {
        FREE_TRUE_LABEL: colors[0] if colors else "#2563eb",
        FREE_FALSE_LABEL: colors[1] if len(colors) > 1 else "#f97316",
    }

    fig = px.box(
        data,
        x="freeship_label",
        y="all_time_quantity_sold",
        color="freeship_label",
        color_discrete_map=color_map,
        points=False,
        hover_data={"all_time_quantity_sold": ":,.0f", "seller_name": True},
        labels={"freeship_label": "Chính sách freeship", "all_time_quantity_sold": "Doanh số (log)"},
        title="Biểu đồ 2.1: Phân phối doanh số theo freeship (Boxplot, log scale)",
    )
    fig.update_yaxes(type="log")
    _format_chart(fig, height=430)
    fig.update_layout(showlegend=False)
    return fig


def _top_seller_table(df: pd.DataFrame, n: int) -> pd.DataFrame:
    data = df[(df["seller_name"].notna()) & (df["all_time_quantity_sold"] > 0)].copy()
    if data.empty:
        return pd.DataFrame(columns=["seller_name", "total_sold"])

    top = (
        data.groupby("seller_name", as_index=False)["all_time_quantity_sold"]
        .sum()
        .rename(columns={"all_time_quantity_sold": "total_sold"})
        .sort_values("total_sold", ascending=False)
        .head(n)
    )
    return top


def _chart_22_top_seller_bar(df: pd.DataFrame, colors: list[str]):
    top10 = _top_seller_table(df, n=10)
    if top10.empty:
        return None

    fig = px.bar(
        top10.sort_values("total_sold", ascending=True),
        x="total_sold",
        y="seller_name",
        orientation="h",
        text="total_sold",
        color="total_sold",
        color_continuous_scale=[[0, "#cbd5e1"], [1, colors[0] if colors else "#2563eb"]],
        labels={"total_sold": "Tổng doanh số", "seller_name": "Nhà cung cấp"},
        hover_data={"total_sold": ":,.0f"},
        title="Biểu đồ 2.2: Top 10 nhà cung cấp theo tổng doanh số",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    _format_chart(fig, height=360, x_grid=True, y_grid=False)
    fig.update_layout(coloraxis_showscale=False)
    return fig


def _chart_23_grouped_top5(df: pd.DataFrame, colors: list[str]):
    top5 = _top_seller_table(df, n=5)
    if top5.empty:
        return None

    data = df[df["seller_name"].isin(top5["seller_name"])].copy()
    data = data[(data["all_time_quantity_sold"] > 0) & (data["has_freeship"].notna())]
    if data.empty:
        return None

    data["freeship_label"] = _freeship_label(data["has_freeship"])
    grouped = (
        data.groupby(["seller_name", "freeship_label"], as_index=False)["all_time_quantity_sold"]
        .sum()
        .rename(columns={"all_time_quantity_sold": "total_sold"})
    )

    seller_order = top5["seller_name"].tolist()
    pivot = grouped.pivot(index="seller_name", columns="freeship_label", values="total_sold").fillna(0)
    pivot = pivot.reindex(seller_order)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=seller_order,
            y=pivot.get(FREE_TRUE_LABEL, pd.Series(index=seller_order, dtype=float)).fillna(0),
            name=FREE_TRUE_LABEL,
            marker_color=colors[0] if colors else "#2563eb",
            hovertemplate="Nhà cung cấp: %{x}<br>Freeship: Có<br>Tổng doanh số: %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=seller_order,
            y=pivot.get(FREE_FALSE_LABEL, pd.Series(index=seller_order, dtype=float)).fillna(0),
            name=FREE_FALSE_LABEL,
            marker_color=colors[1] if len(colors) > 1 else "#f97316",
            hovertemplate="Nhà cung cấp: %{x}<br>Freeship: Không<br>Tổng doanh số: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        title="Biểu đồ 2.3: Top 5 seller theo trạng thái freeship",
        xaxis_title="Nhà cung cấp",
        yaxis_title="Tổng doanh số",
    )
    _format_chart(fig, height=360, x_grid=False, y_grid=True)
    fig.update_xaxes(tickangle=-18)
    return fig


def render_rating_policy_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    del heatmap_scale

    required_cols = {
        "rating_average",
        "review_count",
        "all_time_quantity_sold",
        "has_freeship",
    }
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning("Tab 4 thiếu cột dữ liệu bắt buộc: " + ", ".join(missing))
        return

    st.markdown("<div class='tab-page-header'>Tab 4 — Đánh giá & Chính sách Dịch vụ</div>", unsafe_allow_html=True)

    base_df = _prepare_dataframe(df)
    filtered_df, _, freeship_choice = _render_filters(base_df)

    if not freeship_choice:
        st.info("Hãy chọn ít nhất một trạng thái freeship để hiển thị biểu đồ.")
        return
    if filtered_df.empty:
        st.info("Không có dữ liệu sau khi lọc. Hãy mở rộng bộ lọc rating hoặc freeship.")
        return

    st.header("Phần 1: Hiệu ứng đám đông")
    fig11 = _chart_11_scatter(filtered_df, colors)
    if fig11 is None:
        st.caption("Không đủ dữ liệu để vẽ Biểu đồ 1.1.")
    else:
        st.plotly_chart(fig11, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        fig12 = _chart_12_rating_bin(filtered_df, colors)
        if fig12 is None:
            st.caption("Không đủ dữ liệu để vẽ Biểu đồ 1.2.")
        else:
            st.plotly_chart(fig12, width="stretch")
    with c2:
        fig13 = _chart_13_review_bin_line(filtered_df, colors)
        if fig13 is None:
            st.caption("Không đủ dữ liệu để vẽ Biểu đồ 1.3.")
        else:
            st.plotly_chart(fig13, width="stretch")

    st.header("Phần 2: Phân tích Nhà cung cấp & Dịch vụ")
    fig21 = _chart_21_freeship_box(filtered_df, colors)
    if fig21 is None:
        st.caption("Không đủ dữ liệu để vẽ Biểu đồ 2.1.")
    else:
        st.plotly_chart(fig21, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        fig22 = _chart_22_top_seller_bar(filtered_df, colors)
        if fig22 is None:
            st.caption("Không đủ dữ liệu để vẽ Biểu đồ 2.2.")
        else:
            st.plotly_chart(fig22, width="stretch")
    with c4:
        fig23 = _chart_23_grouped_top5(filtered_df, colors)
        if fig23 is None:
            st.caption("Không đủ dữ liệu để vẽ Biểu đồ 2.3.")
        else:
            st.plotly_chart(fig23, width="stretch")
