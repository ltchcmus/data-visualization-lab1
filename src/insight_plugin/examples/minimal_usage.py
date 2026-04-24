from __future__ import annotations

import pandas as pd

from insight_plugin import ChartDefinition, InsightPlugin, make_group_aggregate_builder


# This script demonstrates plugin usage without importing any dashboard module.
def build_plugin() -> InsightPlugin:
    plugin = InsightPlugin.from_gemini_env()

    plugin.register_many(
        [
            ChartDefinition(
                chart_id="q5_discount_threshold",
                tab_id="price",
                title="Discount threshold analysis",
                question="Do higher discount buckets show different average sales?",
                evidence_builder=make_group_aggregate_builder(
                    group_col="discount_rate",
                    value_col="all_time_quantity_sold",
                    agg="mean",
                    top_n=10,
                    min_count=5,
                    ascending=False,
                ),
                tags=("price", "discount", "sales"),
            )
        ]
    )

    return plugin


def demo() -> None:
    df = pd.DataFrame(
        {
            "discount_rate": [5, 10, 20, 20, 30, 35, 5, 10, 15, 25],
            "all_time_quantity_sold": [
                100,
                140,
                300,
                260,
                380,
                410,
                120,
                160,
                220,
                330,
            ],
        }
    )

    plugin = build_plugin()

    insight = plugin.generate_insight(
        chart_id="q5_discount_threshold",
        dataframe=df,
        filter_context={"year_label": "All"},
    )
    print("[INSIGHT]")
    print(insight.headline)
    for bullet in insight.insights:
        print("-", bullet)

    answer = plugin.ask(
        question="Discount nao cho nhom ban tot hon trong mau nay?",
        dataframe=df,
        chart_ids=["q5_discount_threshold"],
    )
    print("\n[CHAT]")
    print(answer.answer)


if __name__ == "__main__":
    demo()
