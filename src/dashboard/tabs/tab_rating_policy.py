from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..format_utils import format_vn
from ..ui_cards import render_metric_strip

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


def _hex_to_rgba(color: str, alpha: float) -> str:
    if color.startswith("#") and len(color) >= 7:
        h = color.lstrip("#")
        return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha})"
    return color


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


def _render_kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    cols = max(1, len(items))
    render_metric_strip(
        [
            {"label": label, "value": value, "icon": icon, "tone": tone}
            for label, value, icon, tone in items
        ],
        compact=True,
        cols=cols,
    )


def _chart_11_scatter(df: pd.DataFrame, colors: list[str], heatmap_scale: str):
    data = df[
        (df["rating_average"].notna())
        & (df["rating_average"] >= 2)
        & (df["review_count"] > 0)
        & (df["all_time_quantity_sold"] > 0)
    ].copy()
    if data.empty:
        return None

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
            colorscale=heatmap_scale,
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
    fig.update_layout(title="Bản đồ nhiệt: Rating vs Review")
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
    line_color = colors[1] if len(colors)>1 else "#d97706"

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
        title="Rating và hiệu quả bán hàng",
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

    # Log-scale bars cannot plot zero, so keep only positive counts on y while preserving labels.
    bar_y = agg["book_count"].where(agg["book_count"] > 0, np.nan)
    positive_counts = agg.loc[agg["book_count"] > 0, "book_count"]

    # Surge point = bin with the largest positive step-up in average sold.
    delta = agg["avg_sold"].diff().fillna(0)
    surge_idx = int(delta.idxmax()) if len(delta) > 0 else 0
    surge_bin = str(agg.loc[surge_idx, "review_bin"])

    fig = go.Figure()

    # Background volume bars (secondary axis) stay subtle to avoid competing with area trend.
    fig.add_trace(
        go.Bar(
            x=agg["review_bin"],
            y=bar_y,
            name="Số lượng đầu sách",
            marker={"color": colors[2] if len(colors)>2 else "#9E9E9E"},
            opacity=0.4,
            text=agg["book_count"],
            texttemplate="%{text:,.0f}",
            textposition="auto",
            yaxis="y2",
            hovertemplate="Nhóm review: %{x}<br>Số lượng đầu sách: %{y:,.0f}<extra></extra>",
        )
    )

    area_line_color = colors[0] if colors else "#2563eb"
    area_fill_color = _hex_to_rgba(area_line_color, 0.50)
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

    y2_range = None
    y2_tick_vals = None
    y2_tick_text = None
    if not positive_counts.empty:
        y2_min = float(positive_counts.min())
        y2_max = float(positive_counts.max())
        if y2_max > y2_min:
            y2_range = [np.log10(y2_min) - 0.05, np.log10(y2_max) + 0.08]
        else:
            y2_range = [np.log10(max(1.0, y2_min)) - 0.3, np.log10(max(1.0, y2_max)) + 0.3]

        # Keep secondary log ticks sparse so zooming does not flood labels.
        exp_min = int(np.floor(np.log10(max(1.0, y2_min))))
        exp_max = int(np.ceil(np.log10(max(1.0, y2_max))))
        raw_ticks = [float(10**e) for e in range(exp_min, exp_max + 1)]
        if len(raw_ticks) > 5:
            step = int(np.ceil(len(raw_ticks) / 5))
            raw_ticks = raw_ticks[::step]
            if raw_ticks[-1] != float(10**exp_max):
                raw_ticks.append(float(10**exp_max))
        y2_tick_vals = raw_ticks
        y2_tick_text = [f"{v:,.0f}" for v in raw_ticks]

    fig.update_layout(
        title="Ngưỡng review tạo bùng phát doanh số",
        xaxis={"title": "Nhóm review_count", "showgrid": False},
        yaxis={
            "title": "Doanh số trung bình",
            "showgrid": True,
            "gridcolor": "#e2e8f0",
            "nticks": 7,
            "tickformat": ",.0f",
            "rangemode": "tozero",
        },
        yaxis2={
            "title": "Số lượng đầu sách",
            "overlaying": "y",
            "side": "right",
            "type": "log",
            "showgrid": False,
            "tickformat": ",.0f",
            "range": y2_range,
            "tickmode": "array" if y2_tick_vals else "auto",
            "tickvals": y2_tick_vals,
            "ticktext": y2_tick_text,
        },
        barmode="overlay",
    )
    # Keep only primary horizontal gridlines; hide secondary-axis grid to reduce clutter.
    _format_chart(fig, height=360, x_grid=False, y_grid=False)
    fig.update_layout(
        yaxis={**fig.layout.yaxis.to_plotly_json(), "showgrid": True, "gridcolor": "#e2e8f0", "nticks": 7},
        yaxis2={**fig.layout.yaxis2.to_plotly_json(), "showgrid": False},
    )
    return fig


def _chart_21_freeship_box(df: pd.DataFrame, colors: list[str]):
    data = df[(df["has_freeship"].notna()) & (df["all_time_quantity_sold"] > 0)].copy()
    if data.empty:
        return None

    data["freeship_label"] = _freeship_label(data["has_freeship"])
    data["log_sales"] = np.log10(data["all_time_quantity_sold"] + 1.0)
    # Surface group-size imbalance directly in category labels.
    counts = data["freeship_label"].value_counts(dropna=False)
    label_false = f"{FREE_FALSE_LABEL} (N={int(counts.get(FREE_FALSE_LABEL, 0)):,})"
    label_true = f"{FREE_TRUE_LABEL} (N={int(counts.get(FREE_TRUE_LABEL, 0)):,})"

    y_false = data.loc[data["freeship_label"] == FREE_FALSE_LABEL, "all_time_quantity_sold"].astype(float)
    y_true = data.loc[data["freeship_label"] == FREE_TRUE_LABEL, "all_time_quantity_sold"].astype(float)
    y_false_log = data.loc[data["freeship_label"] == FREE_FALSE_LABEL, "log_sales"].astype(float)
    y_true_log = data.loc[data["freeship_label"] == FREE_TRUE_LABEL, "log_sales"].astype(float)

    fig = go.Figure()

    if not y_false_log.empty:
        line_color_false = colors[1] if (colors and len(colors) > 1) else "#FF6347"
        fig.add_trace(
            go.Violin(
                x=[label_false] * len(y_false_log),
                y=y_false_log,
                name=label_false,
                legendgroup="freeship_false",
                scalegroup="freeship_false",
                points=False,
                box_visible=True,
                meanline_visible=True,
                line={
                    "color": line_color_false,
                    "width": 1.4
                },
                fillcolor=_hex_to_rgba(line_color_false, 0.55),
                opacity=0.5,
                spanmode="soft",
                scalemode="width",
                width=0.78,
                customdata=y_false,
                hovertemplate="Doanh số: %{customdata:,.0f} cuốn<extra></extra>",
            )
        )

    if not y_true_log.empty:
        line_color_true = colors[0] if colors else "#4169E1"
        fig.add_trace(
            go.Violin(
                x=[label_true] * len(y_true_log),
                y=y_true_log,
                name=label_true,
                legendgroup="freeship_true",
                scalegroup="freeship_true",
                points=False,
                box_visible=True,
                meanline_visible=True,
                line={"color": line_color_true, "width": 1.4},
                fillcolor=_hex_to_rgba(line_color_true, 0.55),
                opacity=0.5,
                spanmode="soft",
                scalemode="width",
                width=0.78,
                customdata=y_true,
                hovertemplate="Doanh số: %{customdata:,.0f} cuốn<extra></extra>",
            )
        )

    _format_chart(fig, height=430)
    fig.update_xaxes(showgrid=False)

    log_tick_vals = [0, 1, 2, 3, 4, 5]
    log_tick_text = ["1", "10", "100", "1K", "10K", "100K"]
    fig.update_yaxes(
        showgrid=True,
        griddash="dot",
        gridcolor="#e5e7eb",
        tickmode="array",
        tickvals=log_tick_vals,
        ticktext=log_tick_text,
    )
    fig.update_layout(
        violinmode="group",
        violingap=0.36,
        title="Phân bố doanh số theo freeship",
        xaxis_title="Chính sách freeship",
        yaxis_title="Tổng doanh số (Thang đo Log)",
        showlegend=False,
    )
    return fig


def _top_seller_table(df: pd.DataFrame, n: int) -> pd.DataFrame:
    # Priority: normalize current_seller for charting; fallback to prepared seller_name.
    seller_col = "current_seller" if "current_seller" in df.columns else "seller_name"
    data = df.copy()
    data["seller_name"] = data[seller_col].astype("string").str.strip().fillna("Không Rõ")
    data.loc[data["seller_name"].isin(["", "<NA>"]), "seller_name"] = "Không Rõ"
    data["seller_name"] = data["seller_name"].str.title()

    data = data[(data["seller_name"].notna()) & (data["all_time_quantity_sold"] > 0)].copy()
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

    total_top10 = float(top10["total_sold"].sum())
    if total_top10 <= 0:
        return None

    top10 = top10.copy()
    top10["share_pct"] = (top10["total_sold"] / total_top10) * 100.0

    def _compact_number(value: float) -> str:
        abs_val = abs(float(value))
        if abs_val >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        if abs_val >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if abs_val >= 1_000:
            return f"{value / 1_000:.0f}K"
        return f"{value:.0f}"

    # Label format example: 4.66M (85%)
    top10["label_text"] = top10.apply(
        lambda r: f"{_compact_number(r['total_sold'])} ({r['share_pct']:.0f}%)",
        axis=1,
    )

    plot_df = top10.sort_values("total_sold", ascending=False)
    bar_color = colors[0] if colors else "#2563eb"

    fig = go.Figure(
        data=[
            go.Bar(
                x=plot_df["total_sold"],
                y=plot_df["seller_name"],
                orientation="h",
                marker={"color": bar_color},
                text=plot_df["label_text"],
                textposition="outside",
                hovertemplate=(
                    "Nhà cung cấp: %{y}<br>"
                    "Tổng doanh số: %{x:,.0f}<br>"
                    "Thị phần trong Top 10: %{customdata:.2f}%<extra></extra>"
                ),
                customdata=plot_df["share_pct"],
                cliponaxis=False,
            )
        ]
    )

    _format_chart(fig, height=390, x_grid=True, y_grid=False)
    fig.update_layout(
        title="Top 10 seller theo doanh số",
        xaxis_title="Tổng doanh số",
        yaxis_title="Nhà cung cấp",
    )
    # Reverse category order so the longest bar is shown at the top.
    fig.update_yaxes(autorange="reversed")
    return fig


def _chart_23_grouped_top5(df: pd.DataFrame, colors: list[str]):
    top5 = _top_seller_table(df, n=5)
    if top5.empty:
        return None

    # Keep seller normalization consistent with chart 2.2, otherwise Top 5 matching can be empty.
    seller_col = "current_seller" if "current_seller" in df.columns else "seller_name"
    data = df.copy()
    data["seller_name"] = data[seller_col].astype("string").str.strip().fillna("Không Rõ")
    data.loc[data["seller_name"].isin(["", "<NA>"]), "seller_name"] = "Không Rõ"
    data["seller_name"] = data["seller_name"].str.title()

    data = data[data["seller_name"].isin(top5["seller_name"])].copy()
    data = data[(data["all_time_quantity_sold"] > 0) & (data["has_freeship"].notna())]
    if data.empty:
        return None

    # Aggregate sales by seller and freeship state, then convert to within-seller percentages.
    data["freeship_label"] = _freeship_label(data["has_freeship"])
    grouped = (
        data.groupby(["seller_name", "freeship_label"], as_index=False)["all_time_quantity_sold"]
        .sum()
        .rename(columns={"all_time_quantity_sold": "total_sold"})
    )

    seller_order = top5["seller_name"].tolist()
    pivot = grouped.pivot(index="seller_name", columns="freeship_label", values="total_sold").fillna(0)
    pivot = pivot.reindex(seller_order)

    seller_totals = pivot.sum(axis=1).replace(0, np.nan)
    pct_true = (pivot.get(FREE_TRUE_LABEL, pd.Series(index=seller_order, dtype=float)) / seller_totals * 100).fillna(0)
    pct_false = (pivot.get(FREE_FALSE_LABEL, pd.Series(index=seller_order, dtype=float)) / seller_totals * 100).fillna(0)

    # Keep labels readable inside bars; hide small segments to avoid overlap.
    text_true = [f"{v:.0f}%" if v > 5 else "" for v in pct_true]
    text_false = [f"{v:.0f}%" if v > 5 else "" for v in pct_false]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=seller_order,
            y=pct_true,
            name=FREE_TRUE_LABEL,
            marker_color=colors[0] if colors else "#4169E1",
            text=text_true,
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="Nhà cung cấp: %{x}<br>Freeship: Có<br>Tỷ trọng: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=seller_order,
            y=pct_false,
            name=FREE_FALSE_LABEL,
            marker_color=colors[1] if len(colors)>1 else "#FF6347",
            text=text_false,
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="Nhà cung cấp: %{x}<br>Freeship: Không<br>Tỷ trọng: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="stack",
        title="Tỷ trọng freeship của Top 5 seller",
        xaxis_title="Nhà cung cấp",
        yaxis_title="Tỷ trọng doanh số theo seller",
    )
    _format_chart(fig, height=380, x_grid=False, y_grid=False)
    fig.update_yaxes(range=[0, 100], ticksuffix="%", showgrid=False, zeroline=False)
    fig.update_xaxes(showgrid=False)
    fig.update_xaxes(tickangle=-18)
    return fig


def _prepare_tab_data(df: pd.DataFrame) -> pd.DataFrame | None:
    required_cols = {
        "rating_average",
        "review_count",
        "all_time_quantity_sold",
        "has_freeship",
    }
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning("Tab thiếu cột dữ liệu bắt buộc: " + ", ".join(missing))
        return None

    prepared = _prepare_dataframe(df)
    if prepared.empty:
        st.info("Không có dữ liệu sau khi áp dụng bộ lọc toàn cục. Hãy mở rộng bộ lọc để tiếp tục.")
        return None
    return prepared


def render_rating_crowd_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    filtered_df = _prepare_tab_data(df)
    if filtered_df is None:
        return

    valid = filtered_df[
        (filtered_df["rating_average"].notna())
        & (filtered_df["review_count"].notna())
        & (filtered_df["all_time_quantity_sold"] > 0)
    ].copy()
    high_rating_ratio = 0.0
    if not valid.empty:
        high_rating_ratio = float((valid["rating_average"] >= 4.5).mean() * 100)

    _render_kpi_row(
        [
            ("Sách có review", format_vn(int((filtered_df["review_count"] > 0).sum())), "book", "blue"),
            ("Rating trung bình", format_vn(float(filtered_df["rating_average"].mean()), 2), "star", "amber"),
            ("Tỷ lệ rating >= 4.5", f"{format_vn(high_rating_ratio, 1)}%", "target", "emerald"),
        ]
    )

    fig11 = _chart_11_scatter(filtered_df, colors, heatmap_scale)
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


def render_rating_seller_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    del heatmap_scale
    filtered_df = _prepare_tab_data(df)
    if filtered_df is None:
        return

    seller_agg = _top_seller_table(filtered_df, n=10)
    top10_total = float(seller_agg["total_sold"].sum()) if not seller_agg.empty else 0.0
    total_sold_all = float(pd.to_numeric(filtered_df["all_time_quantity_sold"], errors="coerce").fillna(0).sum())
    top10_share_all = float(top10_total / total_sold_all * 100) if total_sold_all > 0 else 0.0
    median_seller_sold = float(seller_agg["total_sold"].median()) if not seller_agg.empty else 0.0

    fs = filtered_df["has_freeship"].dropna()
    freeship_ratio = float(fs.eq(True).mean() * 100) if not fs.empty else 0.0

    _render_kpi_row(
        [
            ("Số seller hoạt động", format_vn(int(filtered_df["seller_name"].nunique())), "building", "blue"),
            ("Tỷ lệ có freeship", f"{format_vn(freeship_ratio, 1)}%", "ship", "emerald"),
            ("Top 10 đóng góp", f"{format_vn(top10_share_all, 1)}% doanh số", "target", "slate"),
            ("Doanh số trung vị/seller", format_vn(median_seller_sold, 0), "chart", "blue"),
        ]
    )

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