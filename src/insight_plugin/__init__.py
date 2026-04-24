from .chart_export import (
    apply_highlight_annotations,
    extract_figure_data,
    figure_to_png_bytes,
    is_kaleido_available,
)
from .chart_registry import ChartRegistry
from .contracts import (
    ChatAnswer,
    ChartAttachment,
    ChartDefinition,
    ChartEvidence,
    HighlightAnnotation,
    HighlightResult,
    InsightResult,
    JsonDict,
    ParsedQuestion,
)
from .evidence_builder import (
    build_evidence_packet,
    dataset_overview,
    make_correlation_builder,
    make_group_aggregate_builder,
    make_univariate_numeric_builder,
)
from .highlight_service import HighlightService
from .llm_client import GeminiLLMClient, LLMClientError, RuleBasedLLMClient
from .plugin import InsightPlugin, parse_question_tags

__all__ = [
    "ChartAttachment",
    "ChartDefinition",
    "ChartEvidence",
    "ChartRegistry",
    "ChatAnswer",
    "GeminiLLMClient",
    "HighlightAnnotation",
    "HighlightResult",
    "HighlightService",
    "InsightPlugin",
    "InsightResult",
    "JsonDict",
    "LLMClientError",
    "ParsedQuestion",
    "RuleBasedLLMClient",
    "apply_highlight_annotations",
    "build_evidence_packet",
    "dataset_overview",
    "extract_figure_data",
    "figure_to_png_bytes",
    "is_kaleido_available",
    "make_correlation_builder",
    "make_group_aggregate_builder",
    "make_univariate_numeric_builder",
    "parse_question_tags",
]
