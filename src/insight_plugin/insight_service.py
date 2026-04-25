from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .chart_registry import ChartRegistry
from .contracts import (
    ChartEvidence,
    ImageProviderFn,
    InsightResult,
    JsonDict,
    LLMClient,
)
from .llm_client import LLMClientError
from .prompts import INSIGHT_RESPONSE_SCHEMA, insight_system_prompt
from .response_validator import validate_insight_response


class InsightService:
    """Generates chart-level insight from evidence packets."""

    def __init__(
        self,
        *,
        registry: ChartRegistry,
        llm_client: LLMClient,
        fallback_client: LLMClient | None = None,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self.registry = registry
        self.llm_client = llm_client
        self.fallback_client = fallback_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, InsightResult]] = {}

    def _payload_hash(self, payload: JsonDict) -> str:
        dump = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> InsightResult | None:
        row = self._cache.get(key)
        if row is None:
            return None

        created_at, result = row
        if (time.time() - created_at) > self.cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return result

    def _set_cached(self, key: str, result: InsightResult) -> None:
        self._cache[key] = (time.time(), result)

    def build_chart_evidence(
        self,
        *,
        chart_id: str,
        dataframe: Any,
        filter_context: JsonDict | None = None,
    ) -> ChartEvidence:
        definition = self.registry.get(chart_id)
        evidence_payload = definition.evidence_builder(dataframe, filter_context or {})
        return ChartEvidence(
            chart_id=definition.chart_id,
            tab_id=definition.tab_id,
            title=definition.title,
            question=definition.question,
            evidence=evidence_payload,
            filter_context=filter_context or {},
        )

    def generate(
        self,
        *,
        chart_id: str,
        dataframe: Any,
        filter_context: JsonDict | None = None,
        extra_context: JsonDict | None = None,
        include_image: bool = False,
        image_provider: ImageProviderFn | None = None,
        image_mime_type: str = "image/png",
        force_refresh: bool = False,
        timeout_seconds: int = 30,
    ) -> InsightResult:
        packet = self.build_chart_evidence(
            chart_id=chart_id,
            dataframe=dataframe,
            filter_context=filter_context,
        )

        user_payload: JsonDict = {
            "mode": "insight",
            "chart": {
                "chart_id": packet.chart_id,
                "tab_id": packet.tab_id,
                "title": packet.title,
                "question": packet.question,
            },
            "evidence": packet.evidence,
            "filter_context": packet.filter_context,
            "extra_context": extra_context or {},
        }

        cache_key = self._payload_hash(user_payload)
        if not force_refresh:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        warnings: list[str] = []
        provider_name = getattr(self.llm_client, "name", "unknown")
        media_parts: list[JsonDict] = []

        if include_image and image_provider is not None:
            try:
                image_bytes = image_provider(chart_id)
                if image_bytes:
                    media_parts.append(
                        {
                            "mime_type": image_mime_type,
                            "data": image_bytes,
                        }
                    )
                else:
                    warnings.append("Image provider returned no bytes for this chart.")
            except Exception as exc:
                warnings.append(f"Image provider failed: {type(exc).__name__}: {exc}")

        try:
            raw = self.llm_client.generate_json(
                system_prompt=insight_system_prompt(),
                user_payload=user_payload,
                response_schema=INSIGHT_RESPONSE_SCHEMA,
                media_parts=media_parts,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            if self.fallback_client is None:
                raise
            warnings.append(f"Primary provider failed: {type(exc).__name__}: {exc}")
            provider_name = getattr(self.fallback_client, "name", "fallback")
            raw = self.fallback_client.generate_json(
                system_prompt=insight_system_prompt(),
                user_payload=user_payload,
                response_schema=INSIGHT_RESPONSE_SCHEMA,
                media_parts=media_parts,
                timeout_seconds=timeout_seconds,
            )

        evidence_keys = (
            set(packet.evidence.keys())
            if isinstance(packet.evidence, dict)
            else {"evidence"}
        )
        normalized, validator_warnings = validate_insight_response(
            raw,
            evidence_keys=evidence_keys,
        )
        warnings.extend(validator_warnings)

        result = InsightResult(
            chart_id=packet.chart_id,
            title=packet.title,
            headline=normalized["headline"],
            insights=normalized["insight_bullets"],
            evidence_used=normalized["evidence_used"],
            limitations=normalized["limitations"],
            confidence_note=normalized["confidence_note"],
            warnings=warnings,
            provider=provider_name,
            raw_payload=raw,
        )

        self._set_cached(cache_key, result)
        return result
