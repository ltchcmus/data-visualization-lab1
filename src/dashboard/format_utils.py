from __future__ import annotations


def format_vn(value: float, decimals: int = 0) -> str:
    """Format number with VN locale: `.` thousands, `,` decimal."""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
