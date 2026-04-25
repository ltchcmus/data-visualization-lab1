from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .chart_export import extract_figure_data
from .contracts import HighlightResult, JsonDict, LLMClient
from .prompts import HIGHLIGHT_RESPONSE_SCHEMA, highlight_system_prompt


class HighlightService:
    """Sends chart data to LLM and returns annotation JSON for highlighting."""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        fallback_client: LLMClient | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self.llm_client = llm_client
        self.fallback_client = fallback_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, HighlightResult]] = {}

    # -- cache helpers -------------------------------------------------------

    def _payload_hash(self, payload: JsonDict) -> str:
        dump = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> HighlightResult | None:
        row = self._cache.get(key)
        if row is None:
            return None
        created_at, result = row
        if (time.time() - created_at) > self.cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return result

    def _set_cached(self, key: str, result: HighlightResult) -> None:
        self._cache[key] = (time.time(), result)

    # -- main API ------------------------------------------------------------

    def highlight(
        self,
        *,
        chart_id: str,
        figure: Any,
        title: str = "",
        question: str = "",
        extra_context: JsonDict | None = None,
        include_image: bool = False,
        image_bytes: bytes | None = None,
        image_mime_type: str = "image/png",
        force_refresh: bool = False,
        timeout_seconds: int = 30,
    ) -> HighlightResult:
        """Analyze a Plotly figure and return highlight annotations.

        Parameters
        ----------
        chart_id:
            Identifier for the chart (used for caching).
        figure:
            A Plotly figure object.
        title:
            Chart title (helps LLM understand context).
        question:
            Optional focus question, e.g. "Highlight the peak values".
        extra_context:
            Any additional context dict sent alongside.
        include_image:
            If True and *image_bytes* is provided, send the PNG to the LLM
            alongside the structured data for richer analysis.
        image_bytes:
            Pre-exported PNG bytes (caller may use ``figure_to_png_bytes``).
        force_refresh:
            Bypass cache.
        timeout_seconds:
            LLM call timeout.
        """
        figure_data = extract_figure_data(figure)

        user_payload: JsonDict = {
            "mode": "highlight",
            "chart_id": chart_id,
            "title": title,
            "question": question or "Highlight các điểm nổi bật, xu hướng và giá trị đáng chú ý",
            "figure_data": figure_data,
            "extra_context": extra_context or {},
        }

        cache_key = self._payload_hash(user_payload)
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        warnings: list[str] = []
        provider_name = getattr(self.llm_client, "name", "unknown")

        # Optional image attachment
        media_parts: list[JsonDict] = []
        if include_image and image_bytes:
            media_parts.append(
                {"mime_type": image_mime_type, "data": image_bytes}
            )

        # Call LLM
        try:
            raw = self.llm_client.generate_json(
                system_prompt=highlight_system_prompt(),
                user_payload=user_payload,
                response_schema=HIGHLIGHT_RESPONSE_SCHEMA,
                media_parts=media_parts,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            if self.fallback_client is None:
                raise
            warnings.append(f"Primary provider failed: {type(exc).__name__}: {exc}")
            provider_name = getattr(self.fallback_client, "name", "fallback")
            raw = self.fallback_client.generate_json(
                system_prompt=highlight_system_prompt(),
                user_payload=user_payload,
                response_schema=HIGHLIGHT_RESPONSE_SCHEMA,
                media_parts=media_parts,
                timeout_seconds=timeout_seconds,
            )

        # Normalize response
        annotations = raw.get("annotations", [])
        if not isinstance(annotations, list):
            annotations = []
            warnings.append("LLM did not return an annotations list.")

        # Basic validation — keep only dicts with a valid type
        valid_types = {"label", "region", "trend_line", "line"}
        validated: list[JsonDict] = []
        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            ann_type = str(ann.get("type", "")).lower().strip()
            if ann_type not in valid_types:
                warnings.append(f"Skipped unknown annotation type: {ann.get('type')}")
                continue
            ann["type"] = ann_type
            validated.append(ann)

        if not validated:
            warnings.append("No valid annotations returned by LLM.")

        summary = str(raw.get("summary", "")).strip()
        key_findings = raw.get("key_findings", [])
        if not isinstance(key_findings, list):
            key_findings = [str(key_findings)] if key_findings else []

        result = HighlightResult(
            chart_id=chart_id,
            annotations=validated,
            summary=summary,
            key_findings=[str(f) for f in key_findings],
            warnings=warnings,
            provider=provider_name,
            raw_payload=raw,
        )
        self._set_cached(cache_key, result)
        return result
