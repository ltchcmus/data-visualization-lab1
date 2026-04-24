from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .chart_registry import ChartRegistry
from .contracts import ChatAnswer, ChartAttachment, ImageProviderFn, JsonDict, LLMClient
from .prompts import CHAT_RESPONSE_SCHEMA, chat_system_prompt
from .response_validator import validate_chat_response


class ChatService:
    """Chart-aware QA service with evidence citations and optional image attachments."""

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
        self._cache: dict[str, tuple[float, ChatAnswer]] = {}

    def _payload_hash(self, payload: JsonDict) -> str:
        dump = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> ChatAnswer | None:
        row = self._cache.get(key)
        if row is None:
            return None
        created_at, answer = row
        if (time.time() - created_at) > self.cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return answer

    def _set_cached(self, key: str, answer: ChatAnswer) -> None:
        self._cache[key] = (time.time(), answer)

    def ask(
        self,
        *,
        question: str,
        dataframe: Any,
        chart_ids: list[str] | None = None,
        tab_id: str | None = None,
        filter_context: JsonDict | None = None,
        extra_context: JsonDict | None = None,
        include_images: bool = False,
        image_provider: ImageProviderFn | None = None,
        image_mime_type: str = "image/png",
        force_refresh: bool = False,
        timeout_seconds: int = 30,
    ) -> ChatAnswer:
        resolved_chart_ids = chart_ids or []
        if not resolved_chart_ids and tab_id:
            resolved_chart_ids = [
                definition.chart_id for definition in self.registry.list_by_tab(tab_id)
            ]
        if not resolved_chart_ids:
            resolved_chart_ids = self.registry.list_chart_ids()
        if not resolved_chart_ids:
            raise ValueError("No charts are registered in the plugin registry")

        evidence_bundle: JsonDict = {}
        for chart_id in resolved_chart_ids:
            definition = self.registry.get(chart_id)
            evidence_bundle[chart_id] = {
                "tab_id": definition.tab_id,
                "title": definition.title,
                "question": definition.question,
                "evidence": definition.evidence_builder(
                    dataframe, filter_context or {}
                ),
            }

        user_payload: JsonDict = {
            "mode": "chat",
            "question": question,
            "chart_ids": resolved_chart_ids,
            "tab_id": tab_id,
            "evidence_bundle": evidence_bundle,
            "filter_context": filter_context or {},
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
        image_bytes_by_chart: dict[str, bytes] = {}

        if include_images and image_provider is not None:
            for chart_id in resolved_chart_ids:
                try:
                    content = image_provider(chart_id)
                except Exception as exc:
                    warnings.append(
                        f"Image provider failed for {chart_id}: {type(exc).__name__}: {exc}"
                    )
                    continue
                if content:
                    image_bytes_by_chart[chart_id] = content
                    media_parts.append(
                        {
                            "mime_type": image_mime_type,
                            "data": content,
                        }
                    )

        try:
            raw = self.llm_client.generate_json(
                system_prompt=chat_system_prompt(),
                user_payload=user_payload,
                response_schema=CHAT_RESPONSE_SCHEMA,
                media_parts=media_parts,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            if self.fallback_client is None:
                raise
            warnings.append(f"Primary provider failed: {type(exc).__name__}: {exc}")
            provider_name = getattr(self.fallback_client, "name", "fallback")
            raw = self.fallback_client.generate_json(
                system_prompt=chat_system_prompt(),
                user_payload=user_payload,
                response_schema=CHAT_RESPONSE_SCHEMA,
                media_parts=media_parts,
                timeout_seconds=timeout_seconds,
            )

        normalized, validator_warnings = validate_chat_response(
            raw,
            allowed_chart_ids=set(resolved_chart_ids),
        )
        warnings.extend(validator_warnings)

        attachments: list[ChartAttachment] = []
        if include_images and image_provider is not None:
            selected_for_images = normalized["source_chart_ids"] or resolved_chart_ids
            for chart_id in selected_for_images:
                content = image_bytes_by_chart.get(chart_id)
                if content is None:
                    continue
                if content:
                    attachments.append(
                        ChartAttachment(
                            chart_id=chart_id,
                            filename=f"{chart_id}.png",
                            mime_type="image/png",
                            content=content,
                        )
                    )

        answer = ChatAnswer(
            answer=normalized["answer"],
            evidence_table=normalized["evidence_table"],
            source_chart_ids=normalized["source_chart_ids"],
            limitations=normalized["limitations"],
            warnings=warnings,
            attachments=attachments,
            provider=provider_name,
            raw_payload=raw,
        )

        self._set_cached(cache_key, answer)
        return answer
