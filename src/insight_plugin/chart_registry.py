from __future__ import annotations

from dataclasses import asdict

from .contracts import ChartDefinition, JsonDict


class ChartRegistry:
    """Stores chart metadata and evidence builders in a dashboard-agnostic way."""

    def __init__(self) -> None:
        self._items: dict[str, ChartDefinition] = {}

    def register(self, definition: ChartDefinition, *, overwrite: bool = False) -> None:
        if not overwrite and definition.chart_id in self._items:
            raise ValueError(f"Chart '{definition.chart_id}' already registered")
        self._items[definition.chart_id] = definition

    def register_many(
        self, definitions: list[ChartDefinition], *, overwrite: bool = False
    ) -> None:
        for definition in definitions:
            self.register(definition, overwrite=overwrite)

    def get(self, chart_id: str) -> ChartDefinition:
        if chart_id not in self._items:
            raise KeyError(f"Unknown chart_id: {chart_id}")
        return self._items[chart_id]

    def list_chart_ids(self) -> list[str]:
        return sorted(self._items.keys())

    def list_by_tab(self, tab_id: str) -> list[ChartDefinition]:
        return sorted(
            (item for item in self._items.values() if item.tab_id == tab_id),
            key=lambda item: item.chart_id,
        )

    def list_tab_ids(self) -> list[str]:
        return sorted({item.tab_id for item in self._items.values()})

    def to_manifest(self) -> list[JsonDict]:
        rows: list[JsonDict] = []
        for item in sorted(self._items.values(), key=lambda entry: entry.chart_id):
            row = asdict(item)
            row.pop("evidence_builder", None)
            rows.append(row)
        return rows
