from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

if __package__ in {None, ""}:
    src_dir = Path(__file__).resolve().parents[2]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from insight_plugin import (  # noqa: E402
    ChartDefinition,
    InsightPlugin,
    apply_highlight_annotations,
    figure_to_png_bytes,

    make_group_aggregate_builder,
    make_univariate_numeric_builder,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def _sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "book": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            "discount_rate": [5, 10, 15, 20, 20, 25, 30, 35, 10, 5],
            "all_time_quantity_sold": [120, 180, 220, 320, 290, 350, 410, 450, 170, 130],
            "rating_average": [4.2, 4.4, 4.6, 4.7, 4.5, 4.8, 4.9, 4.9, 4.3, 4.1],
        }
    )


# ---------------------------------------------------------------------------
# Plugin setup
# ---------------------------------------------------------------------------

def _build_plugin() -> InsightPlugin:
    plugin = InsightPlugin.from_gemini_env()
    plugin.register_many(
        [
            ChartDefinition(
                chart_id="demo_discount_sales",
                tab_id="demo_tab",
                title="Discount vs average sold",
                question="Discount bands with higher average sold?",
                evidence_builder=make_group_aggregate_builder(
                    group_col="discount_rate",
                    value_col="all_time_quantity_sold",
                    agg="mean",
                    top_n=8,
                    min_count=1,
                    ascending=False,
                ),
                tags=("discount", "sales"),
            ),
            ChartDefinition(
                chart_id="demo_rating_distribution",
                tab_id="demo_tab",
                title="Rating distribution",
                question="How is rating distributed in current filter?",
                evidence_builder=make_univariate_numeric_builder(
                    column="rating_average"
                ),
                tags=("rating",),
            ),
        ]
    )
    return plugin


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Insight Plugin Demo", layout="wide")
    st.title("Insight Plugin Demo (independent)")

    # -- session state init --------------------------------------------------
    for key, default in [
        ("insight_results", {}),
        ("chat_answer", None),
        ("pending_insight_chart", None),
        ("image_export_ready", None),
        ("highlight_results", {}),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # -- image export check ---------------------------------------------------
    def _check_image_export_ready() -> bool:
        cached = st.session_state.get("image_export_ready")
        if isinstance(cached, bool):
            return cached
        try:
            test_fig = px.scatter(pd.DataFrame({"x": [0], "y": [0]}), x="x", y="y")
            figure_to_png_bytes(test_fig)
        except Exception:
            st.session_state["image_export_ready"] = False
            return False
        st.session_state["image_export_ready"] = True
        return True

    can_export_images = _check_image_export_ready()

    df = _sample_data()
    plugin = _build_plugin()
    chart_figures: dict[str, object] = {}

    def insight_image_provider(chart_id: str) -> bytes | None:
        if not can_export_images:
            return None
        fig = chart_figures.get(chart_id)
        if fig is None:
            return None
        return figure_to_png_bytes(fig)

    # -- helper: render one chart column + insight + highlight ---------------
    def render_chart_column(chart_id: str, fig: object, label: str) -> None:
        chart_figures[chart_id] = fig

        # Show chart (possibly with highlights)
        hl_result = st.session_state["highlight_results"].get(chart_id)
        if hl_result and hl_result.annotations:
            annotated_fig = apply_highlight_annotations(fig, hl_result.annotations)
            st.plotly_chart(annotated_fig, use_container_width=True)
            if hl_result.summary:
                st.info(f"🔍 **Phân tích:** {hl_result.summary}")
            if hl_result.key_findings:
                for finding in hl_result.key_findings:
                    st.write(f"  • {finding}")
            if st.button("Xóa highlight", key=f"btn_clear_hl_{chart_id}"):
                st.session_state["highlight_results"].pop(chart_id, None)
                st.rerun()
        else:
            st.plotly_chart(fig, use_container_width=True)

        # --- Buttons row: Insight + Highlight ---
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button(f"💡 Insight: {label}", key=f"btn_insight_{chart_id}"):
                st.session_state["pending_insight_chart"] = chart_id
        with btn_col2:
            if st.button(f"🎨 Highlight: {label}", key=f"btn_highlight_{chart_id}"):
                with st.spinner("Đang phân tích biểu đồ..."):
                    try:
                        img_bytes = None
                        if can_export_images:
                            try:
                                img_bytes = figure_to_png_bytes(fig)
                            except Exception:
                                pass
                        hl = plugin.highlight(
                            chart_id=chart_id,
                            figure=fig,
                            title=label,
                            include_image=bool(img_bytes),
                            image_bytes=img_bytes,
                        )
                        st.session_state["highlight_results"][chart_id] = hl
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Highlight thất bại: {exc}")

        # --- Insight generation flow ---
        if st.session_state.get("pending_insight_chart") == chart_id:
            send_image = (
                st.radio(
                    "Gửi ảnh biểu đồ kèm insight?",
                    options=["Không gửi", "Có gửi"],
                    index=1,
                    horizontal=True,
                    key=f"opt_image_{chart_id}",
                )
                == "Có gửi"
            )

            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Chạy insight", key=f"btn_{chart_id}_confirm"):
                with st.spinner("Đang tạo insight..."):
                    result = plugin.generate_insight(
                        chart_id=chart_id,
                        dataframe=df,
                        filter_context={"scope": "demo"},
                        include_image=send_image,
                        image_provider=insight_image_provider,
                    )
                st.session_state["insight_results"][chart_id] = result
                st.session_state["pending_insight_chart"] = None
                st.rerun()
            if cancel_col.button("Hủy", key=f"btn_{chart_id}_cancel"):
                st.session_state["pending_insight_chart"] = None
                st.rerun()

        # --- Show insight result ---
        result = st.session_state["insight_results"].get(chart_id)
        if result:
            st.subheader(result.headline)
            for item in result.insights:
                st.write(f"- {item}")
            if result.warnings:
                st.warning(" | ".join(result.warnings))

    # -----------------------------------------------------------------------
    # Chart columns
    # -----------------------------------------------------------------------
    left, right = st.columns(2)

    with left:
        fig_discount = px.bar(
            df.groupby("discount_rate", as_index=False)[
                "all_time_quantity_sold"
            ].mean(),
            x="discount_rate",
            y="all_time_quantity_sold",
            title="Average sold by discount rate",
        )
        render_chart_column("demo_discount_sales", fig_discount, "discount")

    with right:
        fig_rating = px.histogram(
            df, x="rating_average", nbins=8, title="Rating distribution",
        )
        render_chart_column("demo_rating_distribution", fig_rating, "rating")

    # -----------------------------------------------------------------------
    # Chat section with # tag suggestions
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Chat with chart tags")

    # --- Tag suggestion chips ---
    all_chart_ids = plugin.list_chart_ids()
    all_tab_ids = plugin.list_tab_ids()

    st.caption("Chọn biểu đồ / tab liên quan, hoặc gõ `#tag` trong câu hỏi:")

    # Build tag options: charts + tabs + "all"
    tag_options: list[str] = []
    tag_labels: dict[str, str] = {}
    for cid in all_chart_ids:
        tag = f"#{cid}"
        tag_options.append(tag)
        # Try to get a nicer display label from the registry
        try:
            defn = plugin.registry.get(cid)
            tag_labels[tag] = f"📊 {defn.title}"
        except Exception:
            tag_labels[tag] = f"📊 {cid}"
    for tid in all_tab_ids:
        tag = f"#tab:{tid}"
        tag_options.append(tag)
        tag_labels[tag] = f"📁 Tab: {tid}"
    tag_options.append("#all")
    tag_labels["#all"] = "🌐 Tất cả"

    # Multiselect for tag chips
    selected_tags = st.multiselect(
        "Phạm vi biểu đồ",
        options=tag_options,
        format_func=lambda t: tag_labels.get(t, t),
        default=[],
        key="chat_tag_chips",
        placeholder="Chọn biểu đồ hoặc tab...",
    )

    # Question input
    question = st.text_input(
        "Câu hỏi",
        value="Tóm tắt xu hướng và đưa bằng chứng số liệu",
        key="chat_question",
    )

    # --- Resolve scope from both chips and #tags in text ---
    # Parse any inline #tags from the question text
    parsed = plugin.parse_question_tags(question)
    final_question = parsed.cleaned_question or question

    # Merge: tags from chips + tags from question text
    chip_chart_ids: list[str] = []
    chip_tab_id: str | None = None
    use_all = "#all" in selected_tags

    for tag in selected_tags:
        if tag == "#all":
            continue
        if tag.startswith("#tab:"):
            chip_tab_id = tag[5:]
        elif tag.startswith("#"):
            chip_chart_ids.append(tag[1:])

    # Combine chip selection with inline # parsing
    final_chart_ids = list(dict.fromkeys(chip_chart_ids + parsed.chart_ids))  # dedupe
    final_tab_id = chip_tab_id or parsed.tab_id

    if use_all:
        final_chart_ids = []  # empty = plugin uses all charts
        final_tab_id = None

    # Show resolved scope
    if final_chart_ids or final_tab_id or use_all:
        parts: list[str] = []
        if use_all:
            parts.append("🌐 Tất cả biểu đồ")
        if final_chart_ids:
            parts.append(f"📊 `{'`, `'.join(final_chart_ids)}`")
        if final_tab_id:
            parts.append(f"📁 Tab: `{final_tab_id}`")
        st.info("Phạm vi: " + " · ".join(parts))

    # Image checkbox
    def image_provider(chart_id: str) -> bytes | None:
        if not can_export_images:
            return None
        fig = chart_figures.get(chart_id)
        if fig is None:
            return None
        return figure_to_png_bytes(fig)

    include_images_chat = st.checkbox(
        "Gửi ảnh biểu đồ kèm câu hỏi",
        value=can_export_images,
        disabled=not can_export_images,
        key="chk_image_chat",
    )

    # Ask button
    if st.button("Ask", key="btn_ask"):
        with st.spinner("Đang xử lý câu hỏi..."):
            answer = plugin.ask(
                question=final_question,
                dataframe=df,
                chart_ids=final_chart_ids if final_chart_ids else None,
                tab_id=final_tab_id,
                include_images=include_images_chat,
                image_provider=image_provider,
            )
            st.session_state["chat_answer"] = answer

    # Show answer
    answer = st.session_state.get("chat_answer")
    if answer:
        st.markdown(f"**Answer:** {answer.answer}")
        if answer.evidence_table:
            st.markdown("**Evidence table**")
            st.dataframe(pd.DataFrame(answer.evidence_table), use_container_width=True)
        if answer.limitations:
            st.info("Limitations: " + " | ".join(answer.limitations))
        if answer.warnings:
            st.warning("Warnings: " + " | ".join(answer.warnings))
        for attachment in answer.attachments:
            st.download_button(
                label=f"Download {attachment.filename}",
                data=attachment.content,
                file_name=attachment.filename,
                mime=attachment.mime_type,
                key=f"dl_{attachment.chart_id}",
            )


if __name__ == "__main__":
    main()
