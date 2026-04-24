from __future__ import annotations

import plotly.io as pio


CHART_FONT_FAMILY = "Be Vietnam Pro, Noto Sans, Segoe UI, Arial, sans-serif"
CHART_TEXT_COLOR = "#0f172a"


def configure_plotly_template(template_name: str = "plotly_white") -> None:
    """Configure global Plotly typography so all charts use a consistent Vietnamese-friendly font."""
    template = pio.templates[template_name]
    template.layout.update(
        font={"family": CHART_FONT_FAMILY, "size": 13, "color": CHART_TEXT_COLOR},
        title={"font": {"family": CHART_FONT_FAMILY, "size": 18, "color": CHART_TEXT_COLOR}},
        legend={
            "font": {"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR},
            "title": {"font": {"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR}},
        },
    )


def format_vn(value: float | int, decimals: int = 0) -> str:
    """Format numbers with Vietnamese separators: '.' thousands, ',' decimals."""
    if value is None:
        return ""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def apply_chart_style(fig, *, height: int = 300) -> None:
    """Apply consistent axis/font/grid style and height to a Plotly figure."""
    fig.update_layout(
        font={"family": CHART_FONT_FAMILY, "size": 13, "color": CHART_TEXT_COLOR},
        title={
            "font": {"family": CHART_FONT_FAMILY, "size": 18, "color": CHART_TEXT_COLOR},
            "x": 0.02,
        },
        legend={
            "font": {"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR},
            "title": {"font": {"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR}},
        },
        margin=dict(l=20, r=20, t=42, b=24),
        height=height,
    )
    fig.update_xaxes(
        title_font={"family": CHART_FONT_FAMILY, "size": 13, "color": CHART_TEXT_COLOR},
        tickfont={"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )
    fig.update_yaxes(
        title_font={"family": CHART_FONT_FAMILY, "size": 13, "color": CHART_TEXT_COLOR},
        tickfont={"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )
    fig.update_annotations(font={"family": CHART_FONT_FAMILY, "size": 12, "color": CHART_TEXT_COLOR})
