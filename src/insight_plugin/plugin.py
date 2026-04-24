from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .chart_export import apply_highlight_annotations, extract_figure_data
from .chart_registry import ChartRegistry
from .chat_service import ChatService
from .contracts import (
    ChatAnswer,
    ChartDefinition,
    HighlightResult,
    ImageProviderFn,
    InsightResult,
    JsonDict,
    LLMClient,
    ParsedQuestion,
)
from .highlight_service import HighlightService
from .insight_service import InsightService
from .llm_client import GeminiLLMClient, RuleBasedLLMClient


def _load_env_file(env_file_path: Path) -> None:
    if not env_file_path.exists():
        return

    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _bootstrap_env() -> None:
    """Try loading .env files from common project locations.

    This keeps the plugin decoupled from any dashboard-specific loader.
    """

    module_file = Path(__file__).resolve()
    candidate_paths: list[Path] = []

    for parent in [module_file.parent, *module_file.parents]:
        candidate_paths.append(parent / ".env")
        candidate_paths.append(parent / "src" / ".env")

    seen: set[str] = set()
    for candidate in candidate_paths:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        _load_env_file(candidate)


def _split_api_keys(raw: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;\n]+", raw) if item.strip()]


def _collect_gemini_api_keys() -> list[str]:
    keys: list[str] = []

    multi = os.getenv("GEMINI_API_KEYS", "")
    if multi:
        keys.extend(_split_api_keys(multi))

    single = os.getenv("GEMINI_API_KEY", "").strip()
    if single:
        keys.append(single)

    indexed_items = [
        (name, value.strip())
        for name, value in os.environ.items()
        if name.startswith("GEMINI_API_KEY_") and value.strip()
    ]

    def _index_key(item: tuple[str, str]) -> tuple[int, str]:
        name, _ = item
        suffix = name.replace("GEMINI_API_KEY_", "", 1)
        return (int(suffix), name) if suffix.isdigit() else (10**9, name)

    for _, value in sorted(indexed_items, key=_index_key):
        keys.append(value)

    unique: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique


class InsightPlugin:
    """Facade API for chart-level insight generation and chat Q&A."""

    def __init__(
        self,
        *,
        registry: ChartRegistry,
        insight_service: InsightService,
        chat_service: ChatService,
        highlight_service: HighlightService,
    ) -> None:
        self.registry = registry
        self.insight_service = insight_service
        self.chat_service = chat_service
        self.highlight_service = highlight_service

    @classmethod
    def from_clients(
        cls,
        *,
        llm_client: LLMClient,
        fallback_client: LLMClient | None = None,
        insight_cache_ttl_seconds: int = 300,
        chat_cache_ttl_seconds: int = 180,
        highlight_cache_ttl_seconds: int = 300,
    ) -> "InsightPlugin":
        registry = ChartRegistry()
        insight_service = InsightService(
            registry=registry,
            llm_client=llm_client,
            fallback_client=fallback_client,
            cache_ttl_seconds=insight_cache_ttl_seconds,
        )
        chat_service = ChatService(
            registry=registry,
            llm_client=llm_client,
            fallback_client=fallback_client,
            cache_ttl_seconds=chat_cache_ttl_seconds,
        )
        highlight_service = HighlightService(
            llm_client=llm_client,
            fallback_client=fallback_client,
            cache_ttl_seconds=highlight_cache_ttl_seconds,
        )
        return cls(
            registry=registry,
            insight_service=insight_service,
            chat_service=chat_service,
            highlight_service=highlight_service,
        )

    @classmethod
    def from_gemini_env(
        cls,
        *,
        model: str = "gemini-flash-latest",
        fallback_rule_based: bool = True,
        insight_cache_ttl_seconds: int = 300,
        chat_cache_ttl_seconds: int = 180,
        highlight_cache_ttl_seconds: int = 300,
    ) -> "InsightPlugin":
        _bootstrap_env()
        env_model = os.getenv("GEMINI_MODEL", "").strip()
        if env_model:
            model = env_model

        api_keys = _collect_gemini_api_keys()
        if not api_keys:
            if not fallback_rule_based:
                raise ValueError(
                    "No Gemini API key found. Set GEMINI_API_KEY or GEMINI_API_KEYS."
                )
            llm_client = RuleBasedLLMClient()
            fallback_client = None
        else:
            llm_client = GeminiLLMClient(api_keys=api_keys, model=model)
            fallback_client = RuleBasedLLMClient() if fallback_rule_based else None

        return cls.from_clients(
            llm_client=llm_client,
            fallback_client=fallback_client,
            insight_cache_ttl_seconds=insight_cache_ttl_seconds,
            chat_cache_ttl_seconds=chat_cache_ttl_seconds,
            highlight_cache_ttl_seconds=highlight_cache_ttl_seconds,
        )

    # -- registry helpers ---------------------------------------------------

    def register_chart(
        self, definition: ChartDefinition, *, overwrite: bool = False
    ) -> None:
        self.registry.register(definition, overwrite=overwrite)

    def register_many(
        self, definitions: list[ChartDefinition], *, overwrite: bool = False
    ) -> None:
        self.registry.register_many(definitions, overwrite=overwrite)

    def list_chart_ids(self) -> list[str]:
        return self.registry.list_chart_ids()

    def list_tab_ids(self) -> list[str]:
        return self.registry.list_tab_ids()

    # -- insight ------------------------------------------------------------

    def generate_insight(
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
        timeout_seconds: int = 300,
    ) -> InsightResult:
        return self.insight_service.generate(
            chart_id=chart_id,
            dataframe=dataframe,
            filter_context=filter_context,
            extra_context=extra_context,
            include_image=include_image,
            image_provider=image_provider,
            image_mime_type=image_mime_type,
            force_refresh=force_refresh,
            timeout_seconds=timeout_seconds,
        )

    # -- chat ---------------------------------------------------------------

    def ask(
        self,
        *,
        question: str,
        dataframe: Any,
        chart_ids: list[str] | None = None,
        tab_id: str | None = None,
        filter_context: JsonDict | None = None,
        include_images: bool = False,
        image_provider: Any | None = None,
        image_mime_type: str = "image/png",
        timeout_seconds: int = 300,
        force_refresh: bool = False,
    ) -> ChatAnswer:
        return self.chat_service.ask(
            question=question,
            dataframe=dataframe,
            chart_ids=chart_ids,
            tab_id=tab_id,
            filter_context=filter_context,
            include_images=include_images,
            image_provider=image_provider,
            image_mime_type=image_mime_type,
            timeout_seconds=timeout_seconds,
            force_refresh=force_refresh,
        )

    # -- tag parsing --------------------------------------------------------

    def parse_question_tags(self, question: str) -> ParsedQuestion:
        """Parse ``#tag`` references from a question string.

        Supported syntax:
        - ``#chart_id``   → match a registered chart
        - ``#tab:tab_id`` → match a registered tab
        - ``#all``        → select all charts (returns empty chart_ids list)

        Returns a ``ParsedQuestion(cleaned_question, chart_ids, tab_id)``.
        """
        return parse_question_tags(
            question,
            registered_chart_ids=self.registry.list_chart_ids(),
            registered_tab_ids=self.registry.list_tab_ids(),
        )

    # -- highlight ----------------------------------------------------------

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
        timeout_seconds: int = 300,
    ) -> HighlightResult:
        """Send chart data to LLM and get annotation highlights.

        Does **not** require kaleido — chart data is extracted from the
        Plotly figure JSON directly.  If you also want to send the PNG
        image for richer analysis, pass ``include_image=True`` together
        with ``image_bytes`` from ``figure_to_png_bytes()``.
        """
        return self.highlight_service.highlight(
            chart_id=chart_id,
            figure=figure,
            title=title,
            question=question,
            extra_context=extra_context,
            include_image=include_image,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
            force_refresh=force_refresh,
            timeout_seconds=timeout_seconds,
        )

    def highlight_figure(
        self,
        *,
        chart_id: str,
        figure: Any,
        title: str = "",
        question: str = "",
        extra_context: JsonDict | None = None,
        include_image: bool = False,
        image_bytes: bytes | None = None,
        force_refresh: bool = False,
        timeout_seconds: int = 300,
    ) -> tuple[Any, HighlightResult]:
        """Convenience: highlight + apply annotations → (new_figure, result).

        Returns a **new** Plotly figure with annotations already applied,
        alongside the raw ``HighlightResult`` for inspection.
        """
        result = self.highlight(
            chart_id=chart_id,
            figure=figure,
            title=title,
            question=question,
            extra_context=extra_context,
            include_image=include_image,
            image_bytes=image_bytes,
            force_refresh=force_refresh,
            timeout_seconds=timeout_seconds,
        )
        annotated_fig = apply_highlight_annotations(figure, result.annotations)
        return annotated_fig, result


# ---------------------------------------------------------------------------
# Standalone tag parser (usable without plugin instance)
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"#(\S+)")


def parse_question_tags(
    question: str,
    registered_chart_ids: list[str],
    registered_tab_ids: list[str],
) -> ParsedQuestion:
    """Parse ``#tag`` references from a question string.

    Supported syntax:
    - ``#chart_id``   → exact match to a registered chart
    - ``#tab:tab_id`` → exact match to a registered tab
    - ``#all``        → means "all charts" (returns empty lists)
    - Partial matches are attempted if no exact match found.

    Returns ``ParsedQuestion(cleaned_question, chart_ids, tab_id)``.
    """
    tags = _TAG_RE.findall(question)
    if not tags:
        return ParsedQuestion(question.strip(), [], None)

    chart_ids: list[str] = []
    tab_id: str | None = None

    chart_set = set(registered_chart_ids)
    tab_set = set(registered_tab_ids)

    for tag in tags:
        low = tag.lower()

        # #all → select everything
        if low == "all":
            continue

        # #tab:xxx → explicit tab reference
        if low.startswith("tab:"):
            tid = tag[4:]
            if tid in tab_set:
                tab_id = tid
            else:
                # partial match
                for candidate in registered_tab_ids:
                    if tid.lower() in candidate.lower():
                        tab_id = candidate
                        break
            continue

        # exact chart match
        if tag in chart_set:
            chart_ids.append(tag)
            continue

        # exact tab match (without prefix)
        if tag in tab_set:
            tab_id = tag
            continue

        # partial chart match
        matched = False
        for cid in registered_chart_ids:
            if low in cid.lower() or cid.lower() in low:
                chart_ids.append(cid)
                matched = True
                break

        if not matched:
            # partial tab match
            for tid in registered_tab_ids:
                if low in tid.lower() or tid.lower() in low:
                    tab_id = tid
                    break

    # Remove tags from question text but keep it readable
    cleaned = _TAG_RE.sub("", question).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    return ParsedQuestion(cleaned, chart_ids, tab_id)
