from __future__ import annotations

import base64
import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .contracts import JsonDict


class LLMClientError(RuntimeError):
    pass


_RETRYABLE_HTTP_STATUS = {401, 403, 429, 500, 502, 503, 504}


def _split_api_keys(raw: str) -> list[str]:
    parts = re.split(r"[,;\n]+", raw)
    keys = [part.strip() for part in parts if part.strip()]
    return keys


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _extract_json_object(raw_text: str) -> JsonDict:
    text = raw_text.strip()
    if not text:
        raise LLMClientError("LLM returned empty text")

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise LLMClientError("Could not extract JSON object from LLM response")

    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMClientError("Invalid JSON object from LLM response") from exc

    if not isinstance(obj, dict):
        raise LLMClientError("LLM JSON response is not an object")
    return obj


def _extract_text_from_gemini_response(payload: JsonDict) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LLMClientError("Gemini response does not contain candidates")

    first = candidates[0]
    content = first.get("content", {})
    parts = content.get("parts", [])
    if not isinstance(parts, list) or not parts:
        raise LLMClientError("Gemini response does not contain text parts")

    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return part["text"]

    raise LLMClientError("Gemini response text not found")


class GeminiLLMClient:
    """Gemini REST client with no third-party dependency."""

    name = "gemini-rest"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        model: str = "gemini-flash-latest",
        api_version: str = "v1beta",
    ) -> None:
        env_multi = _split_api_keys(os.getenv("GEMINI_API_KEYS", ""))
        env_single = os.getenv("GEMINI_API_KEY", "").strip()

        merged_keys: list[str] = []
        if api_keys:
            merged_keys.extend([key.strip() for key in api_keys if key and key.strip()])
        if api_key and api_key.strip():
            merged_keys.append(api_key.strip())
        merged_keys.extend(env_multi)
        if env_single:
            merged_keys.append(env_single)

        self._api_keys = _dedupe_preserve_order(merged_keys)
        self.model = model
        self.api_version = api_version
        self._key_index = 0
        self._key_lock = threading.Lock()
        self.name = f"gemini-rest:{self.model}:keys={len(self._api_keys)}"

        if not self._api_keys:
            raise ValueError("Missing GEMINI_API_KEY or GEMINI_API_KEYS")

    def _next_api_key(self) -> str:
        with self._key_lock:
            key = self._api_keys[self._key_index % len(self._api_keys)]
            self._key_index = (self._key_index + 1) % len(self._api_keys)
        return key

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: JsonDict,
        response_schema: JsonDict,
        media_parts: list[dict[str, Any]] | None = None,
        timeout_seconds: int = 30,
    ) -> JsonDict:
        endpoint = (
            f"https://generativelanguage.googleapis.com/{self.api_version}/models/"
            f"{urllib.parse.quote(self.model)}:generateContent"
        )

        content_parts: list[JsonDict] = [
            {
                "text": json.dumps(
                    {
                        "response_schema": response_schema,
                        "payload": user_payload,
                        "instructions": [
                            "Return JSON only.",
                            "Do not include markdown code fences.",
                        ],
                    },
                    ensure_ascii=False,
                )
            }
        ]

        for part in media_parts or []:
            data = part.get("data")
            mime_type = (
                str(part.get("mime_type", "")).strip() or "application/octet-stream"
            )
            if not isinstance(data, (bytes, bytearray)):
                continue
            content_parts.append(
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": base64.b64encode(bytes(data)).decode("ascii"),
                    }
                }
            )

        request_payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": content_parts,
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
        last_error: str | None = None

        for attempt in range(len(self._api_keys)):
            api_key = self._next_api_key()
            request = urllib.request.Request(
                endpoint,
                data=body,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-goog-api-key": api_key,
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(
                    request, timeout=timeout_seconds
                ) as response:
                    raw_response = response.read().decode("utf-8")
                try:
                    payload = json.loads(raw_response)
                except json.JSONDecodeError as exc:
                    raise LLMClientError("Gemini returned non-JSON response") from exc

                text = _extract_text_from_gemini_response(payload)
                return _extract_json_object(text)

            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = f"Gemini HTTPError {exc.code}: {detail}"

                should_retry = (
                    len(self._api_keys) > 1
                    and attempt < (len(self._api_keys) - 1)
                    and exc.code in _RETRYABLE_HTTP_STATUS
                )
                if should_retry:
                    continue
                raise LLMClientError(last_error) from exc

            except urllib.error.URLError as exc:
                last_error = f"Gemini URLError: {exc.reason}"
                should_retry = len(self._api_keys) > 1 and attempt < (
                    len(self._api_keys) - 1
                )
                if should_retry:
                    continue
                raise LLMClientError(last_error) from exc

        raise LLMClientError(last_error or "Gemini request failed on all API keys")


class RuleBasedLLMClient:
    """Deterministic fallback so plugin still works without external API."""

    name = "rule-based"

    def _collect_numeric_entries(
        self, value: Any, prefix: str = ""
    ) -> list[tuple[str, float]]:
        rows: list[tuple[str, float]] = []

        if isinstance(value, dict):
            for key, sub in value.items():
                next_prefix = f"{prefix}.{key}" if prefix else str(key)
                rows.extend(self._collect_numeric_entries(sub, next_prefix))
            return rows

        if isinstance(value, list):
            for idx, sub in enumerate(value[:15]):
                next_prefix = f"{prefix}[{idx}]"
                rows.extend(self._collect_numeric_entries(sub, next_prefix))
            return rows

        if isinstance(value, (int, float)):
            rows.append((prefix or "value", float(value)))
        return rows

    def _top_level_key(self, path: str) -> str:
        top = path.split(".", 1)[0]
        top = top.split("[", 1)[0]
        return top or path

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: JsonDict,
        response_schema: JsonDict,
        media_parts: list[dict[str, Any]] | None = None,
        timeout_seconds: int = 30,
    ) -> JsonDict:
        mode = str(user_payload.get("mode", "insight")).lower()

        if mode == "highlight":
            return self._highlight_fallback(user_payload)

        if mode == "chat":
            question = str(user_payload.get("question", "")).strip()
            chart_ids = user_payload.get("chart_ids", [])
            evidence = user_payload.get("evidence_bundle", {})
            numeric = self._collect_numeric_entries(evidence)
            top = sorted(numeric, key=lambda row: abs(row[1]), reverse=True)[:5]

            evidence_table = [
                {
                    "metric": key,
                    "value": round(value, 4),
                    "source": "evidence_bundle",
                }
                for key, value in top
            ]

            return {
                "answer": (
                    "Rule-based fallback answer. "
                    f"Question: {question}. "
                    "Use this output when Gemini API is unavailable."
                ),
                "evidence_table": evidence_table,
                "source_chart_ids": [str(chart_id) for chart_id in chart_ids],
                "limitations": [
                    "Generated without external LLM.",
                    "Narrative quality is lower than Gemini mode.",
                ],
            }

        chart = user_payload.get("chart", {})
        title = str(chart.get("title", "Chart"))
        evidence = user_payload.get("evidence", {})
        numeric = self._collect_numeric_entries(evidence)
        top = sorted(numeric, key=lambda row: abs(row[1]), reverse=True)[:3]

        bullets = [f"{key} = {round(value, 4)}" for key, value in top]
        if not bullets:
            bullets = ["No numeric evidence could be extracted from current payload."]

        evidence_used: list[str] = []
        for key, _ in top:
            mapped = self._top_level_key(key)
            if mapped not in evidence_used:
                evidence_used.append(mapped)
        if not evidence_used:
            evidence_used = ["evidence"]

        return {
            "headline": f"Insight summary for {title}",
            "insight_bullets": bullets,
            "evidence_used": evidence_used,
            "limitations": [
                "Rule-based fallback was used.",
                "Switch to Gemini for richer language output.",
            ],
            "confidence_note": "medium",
        }

    def _highlight_fallback(self, user_payload: JsonDict) -> JsonDict:
        """Generate simple highlight annotations from figure trace data."""
        fig_data = user_payload.get("figure_data", {})
        traces = fig_data.get("traces", [])
        title = str(user_payload.get("title", "Chart"))
        annotations: list[JsonDict] = []

        palette = ["#FF6B6B", "#4ECDC4", "#FFE66D", "#A8E6CF", "#DDA0DD"]
        color_idx = 0

        for trace in traces[:3]:
            x_vals = trace.get("x", [])
            y_vals = trace.get("y", [])
            if not x_vals or not y_vals:
                continue

            # Find numeric y values and their positions
            numeric_pairs = []
            for i, (xv, yv) in enumerate(zip(x_vals, y_vals)):
                try:
                    numeric_pairs.append((xv, float(yv), i))
                except (ValueError, TypeError):
                    continue

            if not numeric_pairs:
                continue

            # Max value annotation
            max_pair = max(numeric_pairs, key=lambda p: p[1])
            annotations.append({
                "type": "label",
                "x": max_pair[0],
                "y": max_pair[1],
                "text": f"Cao nhất: {round(max_pair[1], 2)}",
                "show_arrow": True,
                "color": palette[color_idx % len(palette)],
            })
            color_idx += 1

            # Min value annotation
            min_pair = min(numeric_pairs, key=lambda p: p[1])
            if min_pair != max_pair:
                annotations.append({
                    "type": "label",
                    "x": min_pair[0],
                    "y": min_pair[1],
                    "text": f"Thấp nhất: {round(min_pair[1], 2)}",
                    "show_arrow": True,
                    "color": palette[color_idx % len(palette)],
                })
                color_idx += 1

            # Average line
            avg_val = sum(p[1] for p in numeric_pairs) / len(numeric_pairs)
            if len(numeric_pairs) >= 3:
                annotations.append({
                    "type": "trend_line",
                    "x0": numeric_pairs[0][0],
                    "y0": avg_val,
                    "x1": numeric_pairs[-1][0],
                    "y1": avg_val,
                    "color": "#45B7D1",
                    "dash": "dot",
                    "label": f"TB: {round(avg_val, 2)}",
                })

        return {
            "annotations": annotations,
            "summary": f"Phân tích cơ bản (rule-based) cho {title}",
            "key_findings": [
                "Giá trị cao nhất và thấp nhất được đánh dấu.",
                "Đường trung bình được hiển thị (nếu đủ dữ liệu).",
                "Kết nối Gemini API để có phân tích chi tiết hơn.",
            ],
        }

