"""
charts.py — All Plotly visualization functions for the Book Sales Dashboard.

Each function returns a plotly.graph_objects.Figure ready for st.plotly_chart().
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from style import get_palette, get_sequential, plotly_layout_defaults


# ═══════════════════════════════════════════════════════════════════
# 1️⃣  Discount threshold analysis — combined bar + line chart
# ═══════════════════════════════════════════════════════════════════

def discount_chart(df: pd.DataFrame, colorblind: bool = False) -> go.Figure:
    """Bar + Line chart: avg quantity sold per discount bin with trend line.

    Highlights the bin with the highest average quantity sold.
    """
    palette = get_palette(colorblind)
    work = df[["discount_rate", "all_time_quantity_sold"]].dropna().copy()

    bins = list(range(0, 105, 5))
    labels = [f"{b}–{b+5}%" for b in bins[:-1]]
    work["bin"] = pd.cut(work["discount_rate"], bins=bins, labels=labels, right=False)

    agg = (
        work.groupby("bin", observed=False)
        .agg(
            avg_sold=("all_time_quantity_sold", "mean"),
            total_sold=("all_time_quantity_sold", "sum"),
            count=("all_time_quantity_sold", "size"),
        )
        .reset_index()
    )
    agg = agg[agg["count"] > 0]

    peak_idx = agg["avg_sold"].idxmax()

    bar_colors = [
        palette[0] if i != peak_idx else "#f59e0b"
        for i in agg.index
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=agg["bin"],
            y=agg["avg_sold"],
            name="TB số lượng bán",
            marker_color=bar_colors,
            marker_line=dict(width=0),
            opacity=0.85,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "TB bán: %{y:,.0f}<br>"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=agg["bin"],
            y=agg["total_sold"],
            name="Tổng số lượng bán",
            mode="lines+markers",
            line=dict(color=palette[1], width=3),
            marker=dict(size=7, color=palette[1]),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Tổng bán: %{y:,.0f}<br>"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    # Annotate peak
    peak_row = agg.loc[peak_idx]
    fig.add_annotation(
        x=peak_row["bin"],
        y=peak_row["avg_sold"],
        text=f"▲ Đỉnh: {peak_row['avg_sold']:,.0f}",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#f59e0b",
        font=dict(color="#f59e0b", size=12, family="Inter"),
        bgcolor="rgba(30,41,59,0.9)",
        bordercolor="#f59e0b",
        borderwidth=1,
        borderpad=4,
    )

    layout = plotly_layout_defaults()
    legend_base = layout.pop("legend", {})
    xaxis_base = layout.pop("xaxis", {})
    yaxis_base = layout.pop("yaxis", {})
    fig.update_layout(
        **layout,
        title="Tỷ lệ giảm giá vs Số lượng bán",
        barmode="group",
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            **legend_base,
        ),
    )
    fig.update_xaxes(title_text="Khoảng giảm giá", tickangle=-45, **xaxis_base)
    fig.update_yaxes(title_text="TB số lượng bán", secondary_y=False, **yaxis_base)
    fig.update_yaxes(title_text="Tổng số lượng bán", secondary_y=True, **yaxis_base)

    return fig


# ═══════════════════════════════════════════════════════════════════
# 2️⃣  Pareto chart — 80/20 rule by author revenue
# ═══════════════════════════════════════════════════════════════════

def pareto_chart(
    df: pd.DataFrame,
    top_n: int = 20,
    colorblind: bool = False,
) -> go.Figure:
    """Pareto chart: revenue by author with cumulative % line."""
    palette = get_palette(colorblind)

    work = df[["authors", "price", "all_time_quantity_sold"]].dropna().copy()
    work["revenue"] = work["price"] * work["all_time_quantity_sold"]

    author_rev = (
        work.groupby("authors")["revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    author_rev["cum_pct"] = (
        author_rev["revenue"].cumsum() / author_rev["revenue"].sum() * 100
    )

    # Colour bars: those within 80% get highlight colour
    bar_colors = [
        palette[0] if pct <= 80 else palette[4]
        for pct in author_rev["cum_pct"]
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=author_rev["authors"],
            y=author_rev["revenue"],
            name="Doanh thu (₫)",
            marker_color=bar_colors,
            opacity=0.85,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Doanh thu: %{y:,.0f}₫<br>"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=author_rev["authors"],
            y=author_rev["cum_pct"],
            name="Tích lũy %",
            mode="lines+markers",
            line=dict(color=palette[1], width=3),
            marker=dict(size=7, color=palette[1]),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Tích lũy: %{y:.1f}%<br>"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    # 80% reference line
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="#f59e0b",
        line_width=1.5,
        annotation_text="80%",
        annotation_position="top right",
        annotation_font=dict(color="#f59e0b", size=12),
        secondary_y=True,
    )

    layout = plotly_layout_defaults()
    legend_base = layout.pop("legend", {})
    xaxis_base = layout.pop("xaxis", {})
    yaxis_base = layout.pop("yaxis", {})
    fig.update_layout(
        **layout,
        title=f"Top {top_n} tác giả theo doanh thu (Pareto)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            **legend_base,
        ),
    )
    fig.update_xaxes(title_text="Tác giả", tickangle=-45, **xaxis_base)
    fig.update_yaxes(title_text="Doanh thu (₫)", secondary_y=False, **yaxis_base)
    fig.update_yaxes(
        title_text="Tích lũy %", range=[0, 105],
        secondary_y=True, **yaxis_base,
    )

    return fig


# ═══════════════════════════════════════════════════════════════════
# 3️⃣ a  Bubble chart — Rating × Review × Quantity
# ═══════════════════════════════════════════════════════════════════

def bubble_chart(df: pd.DataFrame, colorblind: bool = False) -> go.Figure:
    """Bubble chart: rating vs review count, sized by quantity sold."""
    palette = get_palette(colorblind)

    work = df[[
        "name", "rating_average", "review_count",
        "all_time_quantity_sold", "cat_level_3",
    ]].dropna().copy()

    # Sample for performance if very large
    if len(work) > 3000:
        work = work.sample(3000, random_state=42)

    # Cap bubble size for readability
    max_sold = work["all_time_quantity_sold"].max()
    work["size"] = (work["all_time_quantity_sold"] / max_sold * 40).clip(lower=3)

    cats = work["cat_level_3"].unique().tolist()[:8]
    color_map = {c: palette[i % len(palette)] for i, c in enumerate(cats)}

    fig = go.Figure()

    for cat in cats:
        sub = work[work["cat_level_3"] == cat]
        fig.add_trace(
            go.Scatter(
                x=sub["rating_average"],
                y=sub["review_count"],
                mode="markers",
                name=cat.replace("-", " ").title()[:25],
                marker=dict(
                    size=sub["size"],
                    color=color_map[cat],
                    opacity=0.65,
                    line=dict(width=0.5, color="#0f172a"),
                ),
                text=sub["name"].str[:50],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Đánh giá: %{x:.1f}⭐<br>"
                    "Nhận xét: %{y:,}<br>"
                    "Đã bán: %{customdata:,}<br>"
                    "<extra></extra>"
                ),
                customdata=sub["all_time_quantity_sold"],
            )
        )

    # Remaining categories merged
    remaining = work[~work["cat_level_3"].isin(cats)]
    if not remaining.empty:
        fig.add_trace(
            go.Scatter(
                x=remaining["rating_average"],
                y=remaining["review_count"],
                mode="markers",
                name="Khác",
                marker=dict(
                    size=remaining["size"],
                    color="#64748b",
                    opacity=0.4,
                    line=dict(width=0),
                ),
                text=remaining["name"].str[:50],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Đánh giá: %{x:.1f}⭐<br>"
                    "Nhận xét: %{y:,}<br>"
                    "Đã bán: %{customdata:,}<br>"
                    "<extra></extra>"
                ),
                customdata=remaining["all_time_quantity_sold"],
            )
        )

    layout = plotly_layout_defaults()
    layout.pop("legend", None)
    xaxis_base = layout.pop("xaxis", {})
    yaxis_base = layout.pop("yaxis", {})
    fig.update_layout(
        **layout,
        title="Đánh giá vs Số lượng nhận xét (bong bóng = số lượng bán)",
        xaxis=dict(title="Đánh giá trung bình", **xaxis_base),
        yaxis=dict(title="Số lượng nhận xét", type="log", **yaxis_base),
    )

    return fig


# ═══════════════════════════════════════════════════════════════════
# 3️⃣ b  Correlation heatmap
# ═══════════════════════════════════════════════════════════════════

def heatmap_chart(df: pd.DataFrame, colorblind: bool = False) -> go.Figure:
    """Correlation heatmap for key numeric columns."""
    seq = get_sequential(colorblind)

    cols = [
        "price", "discount_rate", "rating_average",
        "review_count", "all_time_quantity_sold",
    ]
    existing = [c for c in cols if c in df.columns]
    corr = df[existing].corr()

    labels = [c.replace("_", " ").title() for c in corr.columns]

    # Round values for annotation
    z_text = [[f"{v:.2f}" for v in row] for row in corr.values]

    fig = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=labels,
            y=labels,
            colorscale=[
                [0.0, "#D55E00" if colorblind else "#ef4444"], # Red/Vermillion for negative
                [0.5, "#1e293b"],                              # Dark neutral for zero correlation
                [1.0, "#0072B2" if colorblind else "#3b82f6"], # Blue for positive
            ],
            zmin=-1,
            zmax=1,
            text=z_text,
            texttemplate="%{text}",
            textfont=dict(size=13, color="#e2e8f0"),
            hovertemplate=(
                "%{x} × %{y}<br>"
                "Tương quan: %{z:.3f}<br>"
                "<extra></extra>"
            ),
          colorbar=dict(
            title=dict(
                text="r",
                font=dict(color="#e2e8f0") # titlefont chuyển thành title['font']
            ),
            tickfont=dict(color="#cbd5e1"),
        )
        )
    )

    layout = plotly_layout_defaults()
    layout.pop("legend", None)
    xaxis_base = layout.pop("xaxis", {})
    yaxis_base = layout.pop("yaxis", {})
    fig.update_layout(
        **layout,
        title="Ma trận tương quan",
        xaxis=dict(side="bottom", **xaxis_base),
        yaxis=dict(autorange="reversed", **yaxis_base),
        width=550,
        height=500,
    )

    return fig


# ═══════════════════════════════════════════════════════════════════
# 4️⃣  Violin / box plot — Seller & freeship performance
# ═══════════════════════════════════════════════════════════════════

def violin_chart(
    df: pd.DataFrame,
    mode: str = "freeship",
    colorblind: bool = False,
) -> go.Figure:
    """Violin plot comparing quantity sold by freeship status or top sellers."""
    palette = get_palette(colorblind)

    if mode == "freeship":
        work = df[["has_freeship", "all_time_quantity_sold"]].dropna().copy()
        work["group"] = work["has_freeship"].map({True: "Freeship", False: "Không Freeship"})
        groups = ["Không Freeship", "Freeship"]
        colors = [palette[3], palette[4]]
        title = "Số lượng bán: Freeship vs Không Freeship"
    else:
        # Top 6 sellers by total quantity
        top_sellers = (
            df.groupby("current_seller_name")["all_time_quantity_sold"]
            .sum()
            .nlargest(6)
            .index.tolist()
        )
        work = df[df["current_seller_name"].isin(top_sellers)][
            ["current_seller_name", "all_time_quantity_sold"]
        ].dropna().copy()
        work["group"] = work["current_seller_name"]
        groups = top_sellers
        colors = [palette[i % len(palette)] for i in range(len(groups))]
        title = "Số lượng bán theo Top nhà bán"

    fig = go.Figure()
    for grp, color in zip(groups, colors):
        sub = work[work["group"] == grp]["all_time_quantity_sold"]
        if sub.empty:
            continue
        fig.add_trace(
            go.Violin(
                y=np.log10(sub.clip(lower=1)),
                name=grp[:25],
                box_visible=True,
                meanline_visible=True,
                fillcolor=color,
                opacity=0.7,
                line_color=color,
                marker=dict(color=color, opacity=0.3, size=3),
                hoverinfo="y+name",
            )
        )

    layout = plotly_layout_defaults()
    layout.pop("legend", None)
    layout.pop("xaxis", None)
    yaxis_base = layout.pop("yaxis", {})
    fig.update_layout(
        **layout,
        title=title,
        yaxis=dict(title="log₁₀(số lượng bán)", **yaxis_base),
        showlegend=True,
        violinmode="group",
    )

    return fig
