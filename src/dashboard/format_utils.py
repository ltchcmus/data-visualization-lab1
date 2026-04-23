from __future__ import annotations


def format_vn(value: float | int, decimals: int = 0) -> str:
    """Format numbers with Vietnamese separators: '.' thousands, ',' decimals."""
    if value is None:
        return ""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def apply_chart_style(fig, *, height: int = 380) -> None:
    """Apply consistent axis/font/grid style and height to a Plotly figure."""
    fig.update_layout(
        font={"color": "#000000"},
        title={"font": {"color": "#000000"}},
        margin={"t": 56},
        height=height,
    )
    fig.update_xaxes(
        title_font={"color": "#000000"},
        tickfont={"color": "#000000"},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )
    fig.update_yaxes(
        title_font={"color": "#000000"},
        tickfont={"color": "#000000"},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )
