from __future__ import annotations

from html import escape
from textwrap import dedent
from typing import Iterable

import streamlit as st


_TONE_COLORS = {
    "blue": "#1E40AF",
    "amber": "#1E40AF",
    "red": "#EF4444",
    "slate": "#64748B",
    "violet": "#1E40AF",
    "emerald": "#1E40AF",
    "cyan": "#1E40AF",
}


def _icon_svg(kind: str, color: str) -> str:
    common = f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    if kind == "money":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <rect x="3.5" y="6" width="17" height="12" rx="3"></rect>
                    <path d="M8 10h8"></path>
                    <path d="M10 14h4"></path>
                    <circle cx="12" cy="12" r="1.8"></circle>
                </g>
            </svg>
            """
        ).strip()
    if kind == "chart":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M4 19h16"></path>
                    <path d="M7 16V9"></path>
                    <path d="M12 16V6"></path>
                    <path d="M17 16v-4"></path>
                </g>
            </svg>
            """
        ).strip()
    if kind == "star":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M12 4.5l2.85 5.77 6.37.93-4.61 4.5 1.09 6.34L12 18.95 6.3 22.04l1.09-6.34-4.61-4.5 6.37-.93L12 4.5z"></path>
                </g>
            </svg>
            """
        ).strip()
    if kind == "book":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M6 4.5h9.5A2.5 2.5 0 0 1 18 7v11.5a1 1 0 0 1-1.55.83L13.8 17.8a2 2 0 0 0-1.2-.4H6A2.5 2.5 0 0 1 3.5 15V7A2.5 2.5 0 0 1 6 4.5z"></path>
                    <path d="M6 4.5v13.6"></path>
                    <path d="M7.8 8h6.7"></path>
                    <path d="M7.8 11.2h5.2"></path>
                </g>
            </svg>
            """
        ).strip()
    if kind == "target":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <circle cx="12" cy="12" r="8"></circle>
                    <circle cx="12" cy="12" r="3.2"></circle>
                    <path d="M12 3.5v3"></path>
                    <path d="M20.5 12h-3"></path>
                </g>
            </svg>
            """
        ).strip()
    if kind == "tag":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M4.5 12V7a2.5 2.5 0 0 1 2.5-2.5h5l7.5 7.5-7.5 7.5-7.5-7.5z"></path>
                    <circle cx="8.5" cy="8.5" r="1.1"></circle>
                </g>
            </svg>
            """
        ).strip()
    if kind == "percent":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M6 18L18 6"></path>
                    <circle cx="8" cy="8" r="2"></circle>
                    <circle cx="16" cy="16" r="2"></circle>
                </g>
            </svg>
            """
        ).strip()
    if kind == "users":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M17 20v-1.5A4.5 4.5 0 0 0 12.5 14h-1A4.5 4.5 0 0 0 7 18.5V20"></path>
                    <circle cx="12" cy="8" r="3"></circle>
                </g>
            </svg>
            """
        ).strip()
    if kind == "building":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M5 20h14"></path>
                    <path d="M7 20V8l5-3v15"></path>
                    <path d="M12 20V5"></path>
                    <path d="M17 20V9h2v11"></path>
                </g>
            </svg>
            """
        ).strip()
    if kind == "ship":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M4 15h16l-2 4H6l-2-4z"></path>
                    <path d="M12 4v11"></path>
                    <path d="M12 4l4 4h-4"></path>
                </g>
            </svg>
            """
        ).strip()
    if kind == "message":
        return dedent(
            f"""
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <g {common}>
                    <path d="M5 6h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H11l-4.5 3v-3H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"></path>
                    <path d="M8 10h8"></path>
                    <path d="M8 13h5"></path>
                </g>
            </svg>
            """
        ).strip()
    return dedent(
        f"""
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <g {common}>
                <circle cx="12" cy="12" r="8"></circle>
            </g>
        </svg>
        """
    ).strip()


def render_metric_strip(
    items: Iterable[dict[str, str]],
    *,
    compact: bool = False,
) -> None:
    _render_card_grid(items, compact=compact)


def render_kpi_section(
    items: Iterable[dict[str, str]],
    *,
    title: str,
    summary: str,
    footnote: str,
) -> None:
    blocks: list[str] = [
        '<div class="kpi-section">',
        f'<div class="kpi-section-title">{escape(title)}</div>',
        f'<div class="kpi-section-summary">{escape(summary)}</div>',
        '<div class="kpi-section-rule"></div>',
    ]
    blocks.append(_build_card_grid(items, compact=False))
    blocks.extend(
        [
            f'<div class="kpi-section-footnote">{escape(footnote)}</div>',
            "</div>",
        ]
    )
    st.markdown("".join(blocks), unsafe_allow_html=True)


def _build_card_grid(items: Iterable[dict[str, str]], *, compact: bool) -> str:
    classes = "kpi-strip" + (" compact" if compact else "")
    blocks: list[str] = [f'<div class="{classes}">']
    for item in items:
        tone = item.get("tone", "blue")
        color = _TONE_COLORS.get(tone, _TONE_COLORS["blue"])
        icon = _icon_svg(item.get("icon", "dot"), color)
        label = escape(str(item.get("label", "")))
        value = item.get("value", "")
        value_html = str(value)
        subtitle = item.get("subtitle", "")
        subtitle_html = escape(str(subtitle)) if subtitle else ""
        accent = f" accent-{tone}" if tone else ""
        card_parts = [
            f'<div class="kpi-box{accent}">',
            f'<div class="kpi-icon" style="color:{color};">{icon}</div>',
            f'<div class="kpi-lbl">{label}</div>',
            f'<div class="kpi-val">{value_html}</div>',
        ]
        if subtitle_html:
            card_parts.append(f'<div class="kpi-sub">{subtitle_html}</div>')
        card_parts.append("</div>")
        blocks.append("".join(card_parts))
    blocks.append("</div>")
    return "".join(blocks)


def _render_card_grid(
    items: Iterable[dict[str, str]],
    *,
    compact: bool = False,
) -> None:
    st.markdown(_build_card_grid(items, compact=compact), unsafe_allow_html=True)
