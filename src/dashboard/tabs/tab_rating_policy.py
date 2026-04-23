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
    data = df[
        (df["rating_average"].notna())
        & (df["rating_average"] >= 2)
        & (df["review_count"] > 0)
        & (df["all_time_quantity_sold"] > 0)
    ].copy()
    if data.empty:
        return None

    del colors
    x_values = np.sort(data["rating_average"].round(1).unique())

    y_max = int(data["review_count"].max())
    # Human-friendly review buckets are easier to read than auto-generated intervals.
    # Using right-open bins keeps each value assigned to exactly one intuitive range.
    base_edges = [1, 2, 4, 6, 11, 21, 51, 101, 201, 501, 1001, 2001, 5001, 10001]
    y_edges = [edge for edge in base_edges if edge <= y_max + 1]
    if not y_edges:
        y_edges = [1, y_max + 1]
    elif y_edges[-1] <= y_max:
        y_edges.append(y_max + 1)

    y_edges = np.array(y_edges, dtype=int)

    data["rating_bin"] = data["rating_average"].round(1)
    data["review_bin"] = pd.cut(data["review_count"], bins=y_edges, include_lowest=True, right=False)
    data = data[data["review_bin"].notna()].copy()

    grouped = (
        data.groupby(["review_bin", "rating_bin"], observed=False)
        .agg(
            sold_sum=("all_time_quantity_sold", "sum"),
            n_books=("all_time_quantity_sold", "size"),
        )
        .reset_index()
    )

    review_order = sorted(grouped["review_bin"].dropna().unique(), key=lambda i: i.left)
    y_labels = []
    for iv in review_order:
        left = int(iv.left)
        right = int(iv.right - 1)
        if right >= y_max:
            y_labels.append(f"{left:,}+")
        else:
            y_labels.append(f"{left:,} - {right:,}")
    y_map = {iv: lab for iv, lab in zip(review_order, y_labels)}

    grouped["review_label"] = grouped["review_bin"].map(y_map)
    grouped = grouped[grouped["review_label"].notna()]

    sold_pivot = grouped.pivot(index="review_label", columns="rating_bin", values="sold_sum").reindex(index=y_labels, columns=x_values)
    count_pivot = grouped.pivot(index="review_label", columns="rating_bin", values="n_books").reindex(index=y_labels, columns=x_values)

    sold_matrix = sold_pivot.to_numpy(dtype=float)
    count_matrix = count_pivot.to_numpy(dtype=float)
    z_log = np.where(sold_matrix > 0, np.log10(sold_matrix + 1.0), np.nan)

    custom = np.dstack([np.nan_to_num(sold_matrix, nan=0.0), np.nan_to_num(count_matrix, nan=0.0)])
    x_labels = [f"{x:.1f}" for x in x_values]

    fig = go.Figure(
        data=go.Heatmap(
            x=x_labels,
            y=y_labels,
            z=z_log,
            customdata=custom,
            zsmooth=False,
            colorscale="Blues",
            hovertemplate=(
                "Rating Average: %{x}<br>"
                "Review Count: %{y}<br>"
                "Tổng doanh số: %{customdata[0]:,.0f}<br>"
                "Số đầu sách: %{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )

    finite_z = z_log[np.isfinite(z_log)]
    z_max = float(finite_z.max()) if finite_z.size else 1.0
    cb_ticks = list(range(0, int(np.floor(z_max)) + 1))
    if z_max > cb_ticks[-1] + 0.2:
        cb_ticks.append(round(z_max, 2))
    cb_tick_text = [f"{int(round(10 ** v - 1)):,.0f}" for v in cb_ticks]

    fig.update_traces(
        colorbar={
            "title": "Tổng doanh số (thang log màu)",
            "tickvals": cb_ticks,
            "ticktext": cb_tick_text,
        }
    )

    # Keep original criterion: pop out top 1-2 cells by absolute total sold.
    # Visual method: subtle red square-outline to frame the hot cell itself.
    sold_for_rank = np.nan_to_num(sold_matrix, nan=0.0)
    if sold_for_rank.size > 0 and sold_for_rank.max() > 0:
        top_count = min(2, int(np.count_nonzero(sold_for_rank > 0)))
        flat_idx = np.argsort(sold_for_rank.ravel())[::-1][:top_count]

        hot_points = []
        for rank, idx in enumerate(flat_idx, start=1):
            row, col = np.unravel_index(idx, sold_for_rank.shape)
            hot_points.append(
                {
                    "rank": rank,
                    "x": x_labels[col],
                    "y": y_labels[row],
                    "sold": float(sold_for_rank[row, col]),
                    "books": float(count_matrix[row, col]),
                }
            )

        # Arrow callout overlay: anchored at exact cell center (category x/y),
        # then offset in pixels so labels stay clear and readable.
        arrow_offsets = [(-26, -34), (30, -24)]
        for i, p in enumerate(hot_points):
            ax, ay = arrow_offsets[i] if i < len(arrow_offsets) else (32, -24)

            # For category axes, numeric-looking labels (e.g. "4.8") can be parsed as numbers
            # by annotations and drift left/right. Use category indices to lock the arrow tip
            # exactly to the same heatmap cell.
            x_cat = x_labels.index(p["x"])
            y_cat = y_labels.index(p["y"])

            fig.add_annotation(
                x=x_cat,
                y=y_cat,
                xref="x",
                yref="y",
                text=f"Hot {p['rank']}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.4,
                arrowcolor="rgba(185,28,28,0.88)",
                ax=ax,
                ay=ay,
                bgcolor="rgba(255,255,255,0.92)",
                bordercolor="rgba(185,28,28,0.55)",
                borderwidth=1,
                borderpad=3,
                font={"size": 10, "color": "#7f1d1d"},
                align="center",
                hovertext=(
                    f"Hot zone {p['rank']}<br>"
                    f"Rating: {p['x']}<br>"
                    f"Review: {p['y']}<br>"
                    f"Tổng doanh số: {p['sold']:,.0f}<br>"
                    f"Số đầu sách: {p['books']:,.0f}"
                ),
            )

    _format_chart(fig, height=440)
    fig.update_layout(title="Biểu đồ 1.1: 2D Density Heatmap Rating vs Review Count (lọc rating >= 2)")
    fig.update_xaxes(title="Rating Average", type="category", categoryorder="array", categoryarray=x_labels)
    fig.update_yaxes(title="Nhóm Review Count", type="category", categoryorder="array", categoryarray=y_labels)
    return fig


def _chart_12_rating_bin(df: pd.DataFrame, colors: list[str]):
    data = df[(df["rating_average"].notna()) & (df["all_time_quantity_sold"].notna())].copy()
    if data.empty:
        return None

    labels = ["<3", "3-4", "4-4.8", "4.8-5"]
    bins = [-0.001, 3, 4, 4.8, 5.001]
    data["rating_bin"] = pd.cut(data["rating_average"], bins=bins, labels=labels, include_lowest=True, right=True)

    agg = (
        data.groupby("rating_bin", observed=False)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            book_count=("all_time_quantity_sold", "size"),
        )
        .reindex(labels)
        .reset_index()
    )

    bar_color = colors[0] if colors else "#4f6d8a"
    line_color = "#d97706"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=agg["rating_bin"],
            y=agg["avg_sold"],
            name="Doanh số trung bình",
            marker={"color": bar_color},
            opacity=0.7,
            text=agg["avg_sold"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            hovertemplate="Nhóm rating: %{x}<br>Doanh số trung bình: %{y:,.0f}<extra></extra>",
            yaxis="y",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=agg["rating_bin"],
            y=agg["book_count"],
            mode="lines+markers+text",
            name="Số lượng đầu sách",
            line={"color": line_color, "width": 2.6},
            marker={"size": 8, "color": line_color},
            text=agg["book_count"],
            texttemplate="%{text:,.0f}",
            textposition="top center",
            hovertemplate="Nhóm rating: %{x}<br>Số lượng đầu sách: %{y:,.0f}<extra></extra>",
            yaxis="y2",
        )
    )

    _format_chart(fig, height=360, y_grid=True, x_grid=False)
    fig.update_layout(
        title="Biểu đồ 1.2: Sức mạnh của Rating: Hiệu quả bán hàng và Quy mô nhóm",
        xaxis={"title": "Nhóm rating", "showgrid": False},
        yaxis={"title": "Doanh số trung bình", "showgrid": True, "gridcolor": "#e2e8f0"},
        yaxis2={
            "title": "Số lượng đầu sách",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "rangemode": "tozero",
        },
        legend={"orientation": "h", "y": 1.14, "x": 1.0, "xanchor": "right", "yanchor": "bottom"},
    )
    return fig


def _chart_13_review_bin_line(df: pd.DataFrame, colors: list[str]):
    data = df[(df["review_count"].notna()) & (df["all_time_quantity_sold"].notna())].copy()
    if data.empty:
        return None

    # Detailed review bins to locate the threshold where sales momentum accelerates.
    labels = ["0-10", "11-50", "51-100", "101-500", "501-1000", ">1000"]
    bins = [-0.001, 10, 50, 100, 500, 1000, float("inf")]
    data["review_bin"] = pd.cut(data["review_count"], bins=bins, labels=labels, include_lowest=True, right=True)

    agg = (
        data.groupby("review_bin", observed=False)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            book_count=("all_time_quantity_sold", "size"),
        )
        .reindex(labels)
        .reset_index()
    )

    # Fill missing bins for stable rendering and robust surge-point detection.
    agg["avg_sold"] = agg["avg_sold"].fillna(0)
    agg["book_count"] = agg["book_count"].fillna(0)

    # Surge point = bin with the largest positive step-up in average sold.
    delta = agg["avg_sold"].diff().fillna(0)
    surge_idx = int(delta.idxmax()) if len(delta) > 0 else 0
    surge_bin = str(agg.loc[surge_idx, "review_bin"])

    fig = go.Figure()

    # Background volume bars (secondary axis) stay subtle to avoid competing with area trend.
    fig.add_trace(
        go.Bar(
            x=agg["review_bin"],
            y=agg["book_count"],
            name="Số lượng đầu sách",
            marker={"color": "#94a3b8"},
            opacity=0.3,
            yaxis="y2",
            hovertemplate="Nhóm review: %{x}<br>Số lượng đầu sách: %{y:,.0f}<extra></extra>",
        )
    )

    area_line_color = colors[0] if colors else "#2563eb"
    area_fill_color = "rgba(37,99,235,0.50)"
    fig.add_trace(
        go.Scatter(
            x=agg["review_bin"],
            y=agg["avg_sold"],
            mode="lines+markers",
            line={"width": 3.2, "color": area_line_color},
            marker={"size": 11, "color": area_line_color, "line": {"width": 1.2, "color": "#ffffff"}},
            fill="tozeroy",
            fillcolor=area_fill_color,
            hovertemplate=(
                "Nhóm review: %{x}<br>"
                "Doanh số trung bình: %{y:,.0f}<br>"
                "Số lượng đầu sách: %{customdata:,.0f}<extra></extra>"
            ),
            customdata=agg["book_count"],
            name="Doanh số trung bình",
            yaxis="y",
        )
    )

    # Plotly compatibility: add_vline with categorical x can fail on some versions.
    # Use add_shape + add_annotation to keep the same insight marker reliably.
    fig.add_shape(
        type="line",
        x0=surge_bin,
        x1=surge_bin,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line={"dash": "dash", "width": 1.6, "color": "rgba(220,38,38,0.85)"},
    )
    fig.add_annotation(
        x=surge_bin,
        y=1,
        xref="x",
        yref="paper",
        text=f"Điểm bùng phát: {surge_bin}",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font={"size": 10, "color": "#991b1b"},
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor="rgba(220,38,38,0.55)",
        borderwidth=1,
        borderpad=3,
    )

    fig.update_layout(
        title="Biểu đồ 1.3: Hành trình Bùng phát: Cần bao nhiêu Review để tạo ra cú hích doanh số?",
        xaxis={"title": "Nhóm review_count", "showgrid": False},
        yaxis={
            "title": "Doanh số trung bình",
            "showgrid": True,
            "gridcolor": "#e2e8f0",
            "tickformat": ",.0f",
            "rangemode": "tozero",
        },
        yaxis2={
            "title": "Số lượng đầu sách",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "tickformat": ",.0f",
            "rangemode": "tozero",
        },
        barmode="overlay",
    )
    _format_chart(fig, height=360, x_grid=False, y_grid=True)
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
