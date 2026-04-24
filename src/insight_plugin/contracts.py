from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, NamedTuple, Protocol


JsonDict = dict[str, Any]
EvidenceBuilderFn = Callable[[Any, JsonDict | None], JsonDict]
ImageProviderFn = Callable[[str], bytes | None]
MediaPart = dict[str, Any]


class LLMClient(Protocol):
    """Protocol for any JSON-producing LLM backend."""

    name: str

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: JsonDict,
        response_schema: JsonDict,
        media_parts: list[MediaPart] | None = None,
        timeout_seconds: int = 300,
    ) -> JsonDict: ...


@dataclass(frozen=True)
class ChartDefinition:
    chart_id: str
    tab_id: str
    title: str
    question: str
    evidence_builder: EvidenceBuilderFn
    tags: tuple[str, ...] = ()


@dataclass
class ChartEvidence:
    chart_id: str
    tab_id: str
    title: str
    question: str
    evidence: JsonDict
    filter_context: JsonDict = field(default_factory=dict)


@dataclass
class InsightResult:
    chart_id: str
    title: str
    headline: str
    insights: list[str]
    evidence_used: list[str]
    limitations: list[str]
    confidence_note: str
    warnings: list[str] = field(default_factory=list)
    provider: str = "unknown"
    raw_payload: JsonDict = field(default_factory=dict)


@dataclass
class ChartAttachment:
    chart_id: str
    filename: str
    mime_type: str
    content: bytes


@dataclass
class ChatAnswer:
    answer: str
    evidence_table: list[JsonDict]
    source_chart_ids: list[str]
    limitations: list[str]
    warnings: list[str] = field(default_factory=list)
    attachments: list[ChartAttachment] = field(default_factory=list)
    provider: str = "unknown"
    raw_payload: JsonDict = field(default_factory=dict)


@dataclass
class HighlightAnnotation:
    """Single annotation returned by the LLM for chart highlighting."""
    type: str  # "label" | "region" | "trend_line"
    text: str = ""
    x: Any = None
    y: Any = None
    x0: Any = None
    y0: Any = None
    x1: Any = None
    y1: Any = None
    show_arrow: bool = True
    color: str = "#FF6B6B"
    fill_color: str = ""
    font_color: str = "#FFFFFF"
    bg_color: str = ""
    label: str = ""
    dash: str = "solid"


@dataclass
class HighlightResult:
    """Result of chart highlight analysis."""
    chart_id: str
    annotations: list[JsonDict]
    summary: str
    key_findings: list[str]
    warnings: list[str] = field(default_factory=list)
    provider: str = "unknown"
    raw_payload: JsonDict = field(default_factory=dict)


class ParsedQuestion(NamedTuple):
    """Result of parsing #tags from a user question."""
    cleaned_question: str
    chart_ids: list[str]
    tab_id: str | None
