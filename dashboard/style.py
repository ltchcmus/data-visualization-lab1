"""
style.py — Color palettes, accessibility toggle logic, and custom CSS.

The user's prompt explicitly requests Custom CSS for cards, shadows, hover
effects, etc., so we use st.html() for targeted layout enhancements only.
All foundational theming (colors, fonts, radii) is handled in config.toml.
"""
from __future__ import annotations

import streamlit as st

# ───────────────────────── colour palettes ─────────────────────────

DEFAULT_PALETTE: list[str] = [
    "#6366f1",  # indigo
    "#22d3ee",  # cyan
    "#f59e0b",  # amber
    "#ef4444",  # red
    "#10b981",  # emerald
    "#a855f7",  # purple
    "#ec4899",  # pink
    "#14b8a6",  # teal
    "#f97316",  # orange
    "#8b5cf6",  # violet
]

# Okabe-Ito palette — universally safe for colour-vision deficiencies
COLORBLIND_PALETTE: list[str] = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#CC79A7",  # pink
    "#56B4E9",  # sky blue
    "#D55E00",  # vermillion
    "#F0E442",  # yellow
    "#000000",  # black
]

SEQUENTIAL_DEFAULT = [
    "#312e81", "#3730a3", "#4338ca", "#4f46e5",
    "#6366f1", "#818cf8", "#a5b4fc", "#c7d2fe",
    "#e0e7ff", "#eef2ff",
]

SEQUENTIAL_COLORBLIND = [
    "#023858", "#045a8d", "#0570b0", "#3690c0",
    "#74a9cf", "#a6bddb", "#d0d1e6", "#ece7f2",
    "#fff7fb", "#ffffff",
]


def get_palette(colorblind: bool = False) -> list[str]:
    """Return the active categorical palette."""
    return COLORBLIND_PALETTE if colorblind else DEFAULT_PALETTE


def get_sequential(colorblind: bool = False) -> list[str]:
    """Return the active sequential palette."""
    return SEQUENTIAL_COLORBLIND if colorblind else SEQUENTIAL_DEFAULT


# ───────────────────────── plotly layout defaults ──────────────────

def plotly_layout_defaults() -> dict:
    """Shared Plotly layout arguments for a consistent dark look."""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#e2e8f0", size=13),
        title_font=dict(size=18, color="#e2e8f0"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=12),
        ),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(
            gridcolor="#334155",
            zerolinecolor="#475569",
            title_font=dict(size=13),
        ),
        yaxis=dict(
            gridcolor="#334155",
            zerolinecolor="#475569",
            title_font=dict(size=13),
        ),
        hoverlabel=dict(
            bgcolor="#1e293b",
            font_size=13,
            font_color="#e2e8f0",
            bordercolor="#6366f1",
        ),
    )


# ───────────────────────── custom CSS ─────────────────────────────

def inject_custom_css() -> None:
    """Inject KPI card styles and subtle layout polish via CSS.

    Per the user request, we add cards with shadows, hover effects, etc.
    """
    st.html("""<style>
    /* ── KPI card styling ── */
    .st-key-kpi_card [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .st-key-kpi_card [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.20);
    }
    .st-key-kpi_card [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
    }
    .st-key-kpi_card [data-testid="stMetricLabel"] {
        font-weight: 500 !important;
        letter-spacing: 0.02em;
    }

    /* ── Section headers ── */
    .st-key-section_header h3 {
        border-left: 4px solid #6366f1;
        padding-left: 0.75rem;
    }

    /* ── Smooth scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #475569; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #6366f1; }
    </style>""")
