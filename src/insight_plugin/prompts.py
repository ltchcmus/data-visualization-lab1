from __future__ import annotations

from .contracts import JsonDict


INSIGHT_RESPONSE_SCHEMA: JsonDict = {
    "headline": "string",
    "insight_bullets": ["string", "string", "string"],
    "evidence_used": ["string"],
    "limitations": ["string"],
    "confidence_note": "string",
}


CHAT_RESPONSE_SCHEMA: JsonDict = {
    "answer": "string",
    "evidence_table": [
        {
            "metric": "string",
            "value": "string|number",
            "source": "chart_id or evidence_key",
        }
    ],
    "source_chart_ids": ["string"],
    "limitations": ["string"],
}


HIGHLIGHT_RESPONSE_SCHEMA: JsonDict = {
    "annotations": [
        {
            "type": "label | region | trend_line",
            "text": "annotation text in Vietnamese",
            "x": "x data value (for label)",
            "y": "y data value (for label)",
            "x0": "start x (for region/trend_line)",
            "y0": "start y (for region/trend_line)",
            "x1": "end x (for region/trend_line)",
            "y1": "end y (for region/trend_line)",
            "color": "#hex color",
            "show_arrow": "boolean (for label)",
            "label": "short label (for region/trend_line)",
        }
    ],
    "summary": "brief summary of chart analysis in Vietnamese",
    "key_findings": ["finding 1", "finding 2"],
}


def insight_system_prompt() -> str:
    return (
        "You are an evidence-constrained analytics assistant. "
        "Use only the provided evidence payload. "
        "Do not invent numbers, sources, or causality. "
        "Respond in Vietnamese unless user asks another language. "
        "Write insight bullets clearly and meaningfully, not too short. "
        "Each bullet should be 1-2 sentences, ideally 18-35 words, and include at least one numeric cue when possible. "
        "Cover: key pattern, practical meaning, and caveat. "
        "For evidence_used, only list keys from the evidence payload (e.g., 'top_groups', 'summary', 'stats.mean', 'top_groups[0].value'); do not paraphrase. "
        "If evidence is insufficient, explicitly say so in limitations. "
        "Return strict JSON following the schema."
    )


def chat_system_prompt() -> str:
    return (
        "You are an evidence-constrained dashboard copilot. "
        "Answer only from provided chart evidence and user question. "
        "Respond in Vietnamese unless user asks another language. "
        "Prefer clear, structured explanation with practical meaning. "
        "Every key claim must be grounded in numeric evidence. "
        "Never claim causality unless explicitly supported by evidence payload. "
        "Return strict JSON following the schema."
    )


def highlight_system_prompt() -> str:
    return (
        "You are a data visualization expert. "
        "Analyze the provided chart data and return JSON annotations to highlight "
        "key patterns, outliers, and noteworthy data points.\n\n"
        "COORDINATE RULES — very important:\n"
        "- Use EXACT data values from the chart traces for x and y coordinates.\n"
        "- For categorical x-axis, use the exact category name as a string.\n"
        "- For numeric axes, use numeric values within the data range.\n"
        "- For 'label': x,y point to a specific data point. Set show_arrow=true.\n"
        "- For 'region': x0,y0,x1,y1 define a rectangle around an interesting area.\n"
        "- For 'trend_line': x0,y0 → x1,y1 draw a line showing a trend.\n\n"
        "COLOR PALETTE (pick from these):\n"
        "- #FF6B6B (coral) for warnings, negatives, peaks\n"
        "- #4ECDC4 (teal) for trends, positives\n"
        "- #FFE66D (gold) for noteworthy neutral points\n"
        "- #A8E6CF (mint) for positive highlights\n"
        "- #DDA0DD (plum) for comparisons\n"
        "- #45B7D1 (sky blue) for averages, baselines\n\n"
        "Return 2–5 annotations. Write text in Vietnamese. "
        "Keep annotation text short (≤ 8 words). "
        "Return strict JSON following the schema, no markdown fences."
    )
