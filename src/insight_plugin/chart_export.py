from __future__ import annotations

import copy
from typing import Any

from .contracts import JsonDict


# ============================================================================
# PNG export — tries kaleido first, then matplotlib fallback
# ============================================================================

def figure_to_png_bytes(
    figure: Any,
    *,
    width: int = 1280,
    height: int = 720,
    scale: int = 2,
) -> bytes:
    """Export a Plotly figure to PNG bytes.

    Tries three strategies in order:
    1. plotly built-in ``pio.to_image`` (needs kaleido 0.x or plotly >= 6 + kaleido 1.x)
    2. kaleido >= 1.x native ``write_fig_sync`` API
    3. **matplotlib fallback** — recreates the chart in matplotlib (always works)
    """

    # --- Attempt 1: plotly built-in (kaleido 0.x / plotly 6 + kaleido 1.x) ---
    try:
        import plotly.io as pio
        return pio.to_image(
            figure, format="png", width=width, height=height, scale=scale,
        )
    except Exception:
        pass

    # --- Attempt 2: kaleido >= 1.x native API --------------------------------
    try:
        return _export_via_kaleido_v1(figure, width=width, height=height, scale=scale)
    except Exception:
        pass

    # --- Attempt 3: matplotlib fallback (no kaleido at all) ------------------
    return _export_via_matplotlib(figure, width=width, height=height)


def _export_via_kaleido_v1(
    figure: Any,
    *,
    width: int = 1280,
    height: int = 720,
    scale: int = 2,
) -> bytes:
    """Use kaleido >= 1.x write_fig API to export a Plotly figure."""
    import io as _io
    import kaleido

    fig_dict = figure.to_dict()
    buf = _io.BytesIO()

    if hasattr(kaleido, "write_fig_sync"):
        kaleido.write_fig_sync(
            fig_dict, buf, format="png", width=width, height=height, scale=scale,
        )
    elif hasattr(kaleido, "write_fig"):
        import asyncio

        async def _do() -> None:
            await kaleido.write_fig(
                fig_dict, buf, format="png", width=width, height=height, scale=scale,
            )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(asyncio.run, _do()).result(timeout=30)
        else:
            asyncio.run(_do())
    else:
        raise RuntimeError("kaleido 1.x API not found")

    result = buf.getvalue()
    if not result:
        raise RuntimeError("kaleido 1.x returned empty output")
    return result


def _export_via_matplotlib(
    figure: Any,
    *,
    width: int = 1280,
    height: int = 720,
    dpi: int = 120,
) -> bytes:
    """Recreate a Plotly figure in matplotlib and export PNG.

    Supports bar, histogram, scatter, line, and pie charts.
    No kaleido or Chrome required — pure Python with matplotlib.
    """
    import io as _io

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dict = figure.to_dict()
    traces = fig_dict.get("data", [])
    layout = fig_dict.get("layout", {})

    fig_w = width / dpi
    fig_h = height / dpi
    has_pie = any(t.get("type") == "pie" for t in traces)

    mpl_fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)

    # --- Title ---
    title_obj = layout.get("title")
    title = ""
    if isinstance(title_obj, dict):
        title = title_obj.get("text", "")
    elif isinstance(title_obj, str):
        title = title_obj

    # --- Render each trace ---
    for trace in traces:
        trace_type = trace.get("type", "scatter")
        x_raw = trace.get("x", [])
        y_raw = trace.get("y", [])
        name = trace.get("name", "")

        x = x_raw.tolist() if hasattr(x_raw, "tolist") else list(x_raw or [])
        y = y_raw.tolist() if hasattr(y_raw, "tolist") else list(y_raw or [])

        if trace_type == "bar":
            x_str = [str(v) for v in x]
            ax.bar(x_str, y, label=name or None, alpha=0.85)

        elif trace_type == "histogram":
            nbins = trace.get("nbinsx") or 10
            ax.hist(x, bins=nbins, label=name or None, alpha=0.75, edgecolor="white")

        elif trace_type == "pie":
            labels = trace.get("labels", [])
            values = trace.get("values", [])
            if hasattr(labels, "tolist"):
                labels = labels.tolist()
            if hasattr(values, "tolist"):
                values = values.tolist()
            if values:
                ax.pie(values, labels=labels or None, autopct="%1.1f%%", startangle=90)
                ax.set_aspect("equal")

        elif trace_type in ("scatter", "scattergl"):
            mode = trace.get("mode", "lines")
            if x and y:
                if "lines" in mode and "markers" in mode:
                    ax.plot(x, y, "-o", label=name or None, markersize=4)
                elif "lines" in mode:
                    ax.plot(x, y, "-", label=name or None)
                elif "markers" in mode:
                    ax.scatter(x, y, label=name or None, s=20)
                else:
                    ax.plot(x, y, label=name or None)

        else:
            # Generic fallback
            if x and y:
                ax.plot(x, y, label=name or None)

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)

    # --- Axis labels ---
    for axis_key, setter in [("xaxis", ax.set_xlabel), ("yaxis", ax.set_ylabel)]:
        axis_cfg = layout.get(axis_key, {})
        axis_title = axis_cfg.get("title", {})
        if isinstance(axis_title, dict):
            axis_title = axis_title.get("text", "")
        if axis_title:
            setter(str(axis_title))

    if any(t.get("name") for t in traces) and not has_pie:
        ax.legend(fontsize=9, framealpha=0.8)

    if not has_pie:
        ax.grid(True, alpha=0.3, linestyle="--")

    mpl_fig.tight_layout()

    buf = _io.BytesIO()
    mpl_fig.savefig(
        buf, format="png", dpi=dpi, bbox_inches="tight",
        facecolor="white", edgecolor="none",
    )
    plt.close(mpl_fig)
    buf.seek(0)
    data = buf.getvalue()
    if not data:
        raise RuntimeError("matplotlib returned empty PNG")
    return data


def is_kaleido_available() -> bool:
    """Check whether image export is available (kaleido OR matplotlib).

    Returns True if **any** PNG export method works.
    """
    # Check kaleido
    try:
        import kaleido
        kver = getattr(kaleido, "__version__", "0")
        major = int(str(kver).split(".")[0])
        if major >= 1:
            if hasattr(kaleido, "write_fig_sync") or hasattr(kaleido, "write_fig"):
                return True
        else:
            from kaleido.scopes.plotly import PlotlyScope  # noqa: F401
            return True
    except Exception:
        pass

    # Matplotlib fallback
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:
        pass

    return False


# ============================================================================
# Helpers for highlight feature (no kaleido needed)
# ============================================================================

def _safe_list(data: Any, limit: int = 60) -> list:
    """Convert trace data to a plain list, truncated to *limit* items."""
    if data is None:
        return []
    if hasattr(data, "tolist"):
        data = data.tolist()
    if isinstance(data, (list, tuple)):
        return list(data[:limit])
    return [data]


def extract_figure_data(figure: Any) -> JsonDict:
    """Extract structured data from a Plotly figure for LLM analysis.

    This does **not** require kaleido — it reads the figure object directly.
    """
    try:
        fig_dict = figure.to_dict()
    except Exception:
        return {"error": "Cannot read figure object"}

    traces: list[JsonDict] = []
    for trace in fig_dict.get("data", []):
        info: JsonDict = {
            "type": trace.get("type", "unknown"),
            "name": trace.get("name", ""),
        }
        for axis in ("x", "y", "z"):
            raw = trace.get(axis)
            if raw is not None:
                items = _safe_list(raw)
                info[axis] = items
                info[f"{axis}_len"] = len(items)
        for extra_key in ("values", "labels", "text", "marker"):
            val = trace.get(extra_key)
            if val is not None:
                if isinstance(val, dict):
                    info[extra_key] = {
                        k: _safe_list(v) if hasattr(v, "__iter__") and not isinstance(v, str) else v
                        for k, v in val.items()
                    }
                else:
                    info[extra_key] = _safe_list(val) if hasattr(val, "__iter__") and not isinstance(val, str) else val
        traces.append(info)

    layout = fig_dict.get("layout", {})
    layout_info: JsonDict = {}
    for key in ("title", "xaxis", "yaxis", "barmode", "legend"):
        val = layout.get(key)
        if val is None:
            continue
        if isinstance(val, dict):
            layout_info[key] = {
                k: v for k, v in val.items()
                if k in ("title", "text", "type", "range", "categoryorder", "tickvals")
            }
        else:
            layout_info[key] = val

    return {"traces": traces, "layout": layout_info, "trace_count": len(traces)}


def _coerce_coord(value: Any) -> Any:
    """Try to convert a coordinate value to number if it looks numeric."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value  # categorical string — keep as-is
    return value


_DEFAULT_PALETTE = [
    "#FF6B6B",  # coral red
    "#4ECDC4",  # teal
    "#FFE66D",  # warm yellow
    "#A8E6CF",  # mint green
    "#DDA0DD",  # plum
    "#45B7D1",  # sky blue
    "#F7DC6F",  # gold
]


def apply_highlight_annotations(figure: Any, annotations: list[JsonDict]) -> Any:
    """Apply highlight annotations from LLM response onto a Plotly figure.

    Returns a **new** (deep-copied) figure so the original is untouched.
    """
    import math
    fig = copy.deepcopy(figure)
    color_idx = 0

    try:
        fig_dict = fig.to_dict()
        is_log_x = fig_dict.get('layout', {}).get('xaxis', {}).get('type') == 'log'
        is_log_y = fig_dict.get('layout', {}).get('yaxis', {}).get('type') == 'log'
    except Exception:
        is_log_x = getattr(fig.layout.xaxis, 'type', None) == 'log'
        is_log_y = getattr(fig.layout.yaxis, 'type', None) == 'log'

    def _cx(val: Any) -> Any:
        v = _coerce_coord(val)
        if is_log_x and isinstance(v, (int, float)) and v > 0:
            return math.log10(v)
        return v

    def _cy(val: Any) -> Any:
        v = _coerce_coord(val)
        if is_log_y and isinstance(v, (int, float)) and v > 0:
            return math.log10(v)
        return v

    for ann in annotations:
        ann_type = str(ann.get("type", "label")).lower().strip()
        color = ann.get("color") or _DEFAULT_PALETTE[color_idx % len(_DEFAULT_PALETTE)]
        color_idx += 1

        try:
            if ann_type == "label":
                fig.add_annotation(
                    x=_cx(ann.get("x")),
                    y=_cy(ann.get("y")),
                    text=str(ann.get("text", "")),
                    showarrow=bool(ann.get("show_arrow", True)),
                    arrowhead=2,
                    arrowsize=1.5,
                    arrowwidth=2,
                    arrowcolor=color,
                    font=dict(
                        size=int(ann.get("font_size", 13)),
                        color=str(ann.get("font_color", "#FFFFFF")),
                    ),
                    bgcolor=str(ann.get("bg_color", color)),
                    bordercolor=color,
                    borderwidth=1,
                    borderpad=4,
                    opacity=float(ann.get("opacity", 0.92)),
                )

            elif ann_type == "region":
                fill = ann.get("fill_color", "")
                if not fill:
                    fill = _hex_to_rgba(color, 0.13)
                fig.add_shape(
                    type="rect",
                    x0=_cx(ann.get("x0")),
                    y0=_cy(ann.get("y0")),
                    x1=_cx(ann.get("x1")),
                    y1=_cy(ann.get("y1")),
                    fillcolor=fill,
                    line=dict(
                        color=ann.get("border_color", color),
                        width=int(ann.get("border_width", 2)),
                        dash=str(ann.get("dash", "dot")),
                    ),
                )
                label = ann.get("label", "")
                if label:
                    cx = _mid(_cx(ann.get("x0")), _cx(ann.get("x1")))
                    fig.add_annotation(
                        x=cx,
                        y=_cy(ann.get("y1")),
                        text=str(label),
                        showarrow=False,
                        font=dict(size=11, color=color),
                        yshift=14,
                    )

            elif ann_type in ("trend_line", "line"):
                fig.add_shape(
                    type="line",
                    x0=_cx(ann.get("x0")),
                    y0=_cy(ann.get("y0")),
                    x1=_cx(ann.get("x1")),
                    y1=_cy(ann.get("y1")),
                    line=dict(
                        color=color,
                        width=float(ann.get("width", 2.5)),
                        dash=str(ann.get("dash", "dash")),
                    ),
                )
                label = ann.get("label", "")
                if label:
                    fig.add_annotation(
                        x=_cx(ann.get("x1")),
                        y=_cy(ann.get("y1")),
                        text=str(label),
                        showarrow=False,
                        font=dict(size=11, color=color),
                        xshift=10,
                    )
        except Exception:
            continue  # skip broken annotations gracefully

    return fig


def _hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    """Convert ``#RRGGBB`` to ``rgba(r,g,b,a)``."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(200,200,200,{alpha})"
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _mid(a: Any, b: Any) -> Any:
    """Midpoint — works for numeric values, returns *a* for strings."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return (a + b) / 2
    return a
