from __future__ import annotations


def format_vn(value: float | int, decimals: int = 0) -> str:
    """Format numbers with Vietnamese separators: '.' thousands, ',' decimals."""
    if value is None:
        return ""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
