from __future__ import annotations

import re
from typing import Any

from .contracts import JsonDict


_CAUSAL_PATTERNS = (
    "chac chan do",
    "nguyen nhan la",
    "vi vay nen",
    "cause",
    "caused by",
    "because of",
)


def _to_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _contains_number(text: str) -> bool:
    return bool(re.search(r"[-+]?\d[\d,.]*", text))


def _contains_causal_claim(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in _CAUSAL_PATTERNS)


def _is_known_evidence_reference(reference: str, evidence_keys: set[str]) -> bool:
    if reference in evidence_keys:
        return True

    top = reference.split(".", 1)[0]
    top = top.split("[", 1)[0]
    return top in evidence_keys


def validate_insight_response(
    payload: JsonDict, *, evidence_keys: set[str]
) -> tuple[JsonDict, list[str]]:
    warnings: list[str] = []

    headline = str(payload.get("headline", "")).strip()
    insights = _to_list(payload.get("insight_bullets") or payload.get("insights"))
    evidence_used = _to_list(payload.get("evidence_used"))
    limitations = _to_list(payload.get("limitations"))
    confidence_note = str(payload.get("confidence_note", "")).strip()

    if not headline:
        headline = "AI insight summary"
        warnings.append("Missing headline, fallback was applied.")

    if not insights:
        insights = ["No validated insight bullets were generated."]
        warnings.append("Missing insight bullets, fallback was applied.")

    if not evidence_used:
        evidence_used = sorted(evidence_keys)[:3]
        warnings.append("Missing evidence_used, fallback keys were inserted.")

    unknown_keys = [
        key
        for key in evidence_used
        if not _is_known_evidence_reference(key, evidence_keys)
    ]
    if unknown_keys:
        warnings.append(
            f"Insight referenced unknown evidence keys: {', '.join(unknown_keys)}"
        )

    if any(_contains_causal_claim(text) for text in [headline, *insights]):
        warnings.append(
            "Potential causal wording detected. Review before showing to users."
        )

    if not any(_contains_number(text) for text in insights):
        warnings.append("Insight bullets do not contain numeric evidence.")

    normalized = {
        "headline": headline,
        "insight_bullets": insights,
        "evidence_used": evidence_used,
        "limitations": limitations,
        "confidence_note": confidence_note,
    }
    return normalized, warnings


def validate_chat_response(
    payload: JsonDict, *, allowed_chart_ids: set[str]
) -> tuple[JsonDict, list[str]]:
    warnings: list[str] = []

    answer = str(payload.get("answer", "")).strip()
    if not answer:
        answer = "No answer generated. Please try again with a narrower question."
        warnings.append("Missing answer, fallback message was applied.")

    evidence_table_raw = payload.get("evidence_table", [])
    evidence_table: list[JsonDict] = []
    if isinstance(evidence_table_raw, list):
        for row in evidence_table_raw:
            if isinstance(row, dict):
                evidence_table.append({k: row[k] for k in row})

    source_chart_ids = _to_list(payload.get("source_chart_ids"))
    if not source_chart_ids:
        warnings.append("Missing source_chart_ids in chat response.")

    unknown = [
        chart_id for chart_id in source_chart_ids if chart_id not in allowed_chart_ids
    ]
    if unknown:
        warnings.append(
            f"Chat response referenced unknown chart ids: {', '.join(unknown)}"
        )

    limitations = _to_list(payload.get("limitations"))

    if _contains_causal_claim(answer):
        warnings.append("Potential causal wording detected in chat answer.")

    normalized = {
        "answer": answer,
        "evidence_table": evidence_table,
        "source_chart_ids": source_chart_ids,
        "limitations": limitations,
    }
    return normalized, warnings
