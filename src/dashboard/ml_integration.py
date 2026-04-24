"""ML Insight integration for the dashboard.

This module provides:
- A singleton InsightPlugin instance (shared across tabs).
- Chart registrations for all 4 main tabs.
- A ``render_chart_with_ml()`` helper that wraps any Plotly figure
  with a hover-revealed floating ML button.
- A ``render_chat_section()`` helper for the Ask/Chat feature.

The existing chart-building code is **not** modified — only the
``st.plotly_chart(fig, …)`` call is replaced by
``render_chart_with_ml(chart_id, fig, df, …)``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure insight_plugin is importable from the src/ directory.
_src_dir = Path(__file__).resolve().parents[1]
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from insight_plugin import (  # noqa: E402
    ChartDefinition,
    InsightPlugin,
    apply_highlight_annotations,
    figure_to_png_bytes,
    make_correlation_builder,
    make_group_aggregate_builder,
    make_univariate_numeric_builder,
)


# ---------------------------------------------------------------------------
# Singleton plugin
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _get_plugin() -> InsightPlugin:
    plugin = InsightPlugin.from_gemini_env()

    # ── TAB: overview ──────────────────────────────────────────────
    plugin.register_many([
        ChartDefinition(
            chart_id="overview_long_tail",
            tab_id="overview",
            title="Phân bổ doanh số: Hiệu ứng Long-tail",
            question="Phân bổ doanh số có hiệu ứng long-tail không? Nhóm nào chiếm phần lớn?",
            evidence_builder=make_univariate_numeric_builder(column="all_time_quantity_sold"),
            tags=("overview", "sales", "distribution"),
        ),
    ])

    # ── TAB: distribution (sản phẩm) ──────────────────────────────
    plugin.register_many([
        ChartDefinition(
            chart_id="dist_category_boxplot",
            tab_id="distribution",
            title="Hiệu quả bán hàng theo thể loại (Top 15)",
            question="Thể loại nào có doanh số trung bình cao nhất? Có ngoại lệ không?",
            evidence_builder=make_group_aggregate_builder(
                group_col="cat_level_3", value_col="all_time_quantity_sold",
                agg="median", top_n=15, min_count=1, ascending=False,
            ),
            tags=("product", "category", "boxplot"),
        ),
        ChartDefinition(
            chart_id="dist_niche_market",
            tab_id="distribution",
            title="Thị trường ngách: Phân vùng danh mục",
            question="Những danh mục nào thuộc nhóm ngôi sao (high sales + high rating)?",
            evidence_builder=make_correlation_builder(
                columns=["all_time_quantity_sold", "rating_average"],
            ),
            tags=("product", "niche", "quadrant"),
        ),
        ChartDefinition(
            chart_id="dist_pages_vs_sold",
            tab_id="distribution",
            title="Độ dày sách vs Doanh số",
            question="Số trang sách có liên quan đến doanh số không?",
            evidence_builder=make_correlation_builder(
                columns=["number_of_page", "all_time_quantity_sold"],
            ),
            tags=("product", "pages", "scatter"),
        ),
        ChartDefinition(
            chart_id="dist_genre_pages",
            tab_id="distribution",
            title="Phân bố số trang theo Thể loại",
            question="Thể loại nào có nhiều sách dày nhất?",
            evidence_builder=make_group_aggregate_builder(
                group_col="cat_level_3", value_col="number_of_page",
                agg="mean", top_n=12, min_count=1, ascending=False,
            ),
            tags=("product", "pages", "genre"),
        ),
    ])

    # ── TAB: price (giá & chiết khấu) ────────────────────────────
    plugin.register_many([
        ChartDefinition(
            chart_id="price_discount_threshold",
            tab_id="price",
            title="Tương quan Mức giảm giá, Doanh số & Doanh thu",
            question="Mức chiết khấu nào tối ưu nhất cho doanh thu?",
            evidence_builder=make_group_aggregate_builder(
                group_col="discount_rate", value_col="all_time_quantity_sold",
                agg="mean", top_n=10, min_count=1, ascending=False,
            ),
            tags=("price", "discount", "threshold"),
        ),
        ChartDefinition(
            chart_id="price_year_trend",
            tab_id="price",
            title="Doanh số trung bình theo năm xuất bản",
            question="Xu hướng doanh số theo năm xuất bản ra sao?",
            evidence_builder=make_group_aggregate_builder(
                group_col="publication_year", value_col="all_time_quantity_sold",
                agg="mean", top_n=25, min_count=1, ascending=False,
            ),
            tags=("price", "year", "trend"),
        ),
        ChartDefinition(
            chart_id="price_discount_year_trend",
            tab_id="price",
            title="Chiết khấu TB & số đầu sách theo năm",
            question="Chiết khấu trung bình thay đổi thế nào theo năm xuất bản?",
            evidence_builder=make_group_aggregate_builder(
                group_col="publication_year", value_col="discount_rate",
                agg="mean", top_n=25, min_count=1, ascending=False,
            ),
            tags=("price", "discount", "year"),
        ),
    ])

    # ── TAB: publisher (NXB & tác giả) ───────────────────────────
    plugin.register_many([
        ChartDefinition(
            chart_id="pub_top_publishers",
            tab_id="publisher",
            title="Top 15 NXB — Doanh số trung bình",
            question="NXB nào có doanh số trung bình cao nhất?",
            evidence_builder=make_group_aggregate_builder(
                group_col="publisher_vn", value_col="all_time_quantity_sold",
                agg="mean", top_n=15, min_count=5, ascending=False,
            ),
            tags=("publisher", "ranking"),
        ),
        ChartDefinition(
            chart_id="pub_donut",
            tab_id="publisher",
            title="Thị phần theo NXB",
            question="NXB nào chiếm thị phần lớn nhất?",
            evidence_builder=make_group_aggregate_builder(
                group_col="publisher_vn", value_col="all_time_quantity_sold",
                agg="sum", top_n=10, min_count=1, ascending=False,
            ),
            tags=("publisher", "share", "donut"),
        ),
        ChartDefinition(
            chart_id="pub_author_pareto",
            tab_id="publisher",
            title="Pareto: Top 20 tác giả & % Doanh thu tích lũy",
            question="Bao nhiêu phần trăm doanh thu đến từ nhóm tác giả hàng đầu?",
            evidence_builder=make_group_aggregate_builder(
                group_col="authors", value_col="all_time_quantity_sold",
                agg="sum", top_n=20, min_count=1, ascending=False,
            ),
            tags=("author", "pareto"),
        ),
        ChartDefinition(
            chart_id="pub_author_consistency",
            tab_id="publisher",
            title="Tác giả: Ổn định vs Siêu phẩm",
            question="Tác giả nào ổn định đều tay, tác giả nào phụ thuộc siêu phẩm?",
            evidence_builder=make_correlation_builder(
                columns=["all_time_quantity_sold", "price", "rating_average"],
            ),
            tags=("author", "consistency", "scatter"),
        ),
    ])

    return plugin


def get_plugin() -> InsightPlugin:
    """Return the shared InsightPlugin singleton."""
    return _get_plugin()


# ---------------------------------------------------------------------------
# Session-state initialization
# ---------------------------------------------------------------------------

def _init_ml_state() -> None:
    """Ensure all ML-related session state keys exist."""
    for key, default in [
        ("ml_insight_results", {}),
        ("ml_highlight_results", {}),
        ("ml_pending_insight_chart", None),
        ("ml_image_export_ready", None),
        ("ml_chart_figures", {}),
        ("ml_chat_answer", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _check_image_export() -> bool:
    """Probe once per session whether PNG export works."""
    cached = st.session_state.get("ml_image_export_ready")
    if isinstance(cached, bool):
        return cached
    try:
        test_fig = px.scatter(pd.DataFrame({"x": [0], "y": [0]}), x="x", y="y")
        figure_to_png_bytes(test_fig)
    except Exception:
        st.session_state["ml_image_export_ready"] = False
        return False
    st.session_state["ml_image_export_ready"] = True
    return True


# ---------------------------------------------------------------------------
# Public API: render a chart with hover-floating ML button
# ---------------------------------------------------------------------------

_UNIQUE_COUNTER_KEY = "__ml_render_counter"

@st.dialog("🎨 Chi tiết Highlight", width="large")
def show_highlight_dialog(chart_id: str, fig: Any, hl_result: Any):
    annotated_fig = apply_highlight_annotations(fig, hl_result.annotations)
    st.plotly_chart(annotated_fig, use_container_width=True, key=f"ml_dlg_{chart_id}")
    
    if hl_result.summary:
        st.info(f"🔍 **Phân tích:** {hl_result.summary}")
    if hl_result.key_findings:
        for finding in hl_result.key_findings:
            st.write(f"  • {finding}")


def render_chart_with_ml(
    chart_id: str,
    fig: object,
    df: pd.DataFrame,
    *,
    label: str = "",
    filter_context: dict[str, Any] | None = None,
    use_container_width: bool = True,
) -> None:
    """Render a Plotly chart with a hover-revealed floating ML button.

    This replaces the plain ``st.plotly_chart(fig, ...)`` call.
    Existing chart-building code is **not** changed.

    UX design:
    - The chart is rendered normally inside a wrapper div.
    - A small floating "🤖" button appears at the **bottom-right corner**
      of the chart ONLY when the user hovers over the chart area.
    - Clicking that button opens a popover with ML actions.
    - The wrapper uses a unique CSS class ``ml-chart-wrap`` so the
      hover show/hide can be done purely in CSS.
    """
    _init_ml_state()
    can_export = _check_image_export()
    plugin = get_plugin()

    # Store figure reference for image export
    st.session_state["ml_chart_figures"][chart_id] = fig

    # ── Check for existing highlights ─────────────────────────────
    hl_result = st.session_state["ml_highlight_results"].get(chart_id)

    # ── Render: chart + floating popover inside a container ───────
    # We use a sentinel HTML div with a unique class so CSS can scope
    # the hover effect to the immediate parent container.
    st.markdown(
        f'<div class="ml-chart-wrap" data-chartid="{chart_id}"></div>',
        unsafe_allow_html=True,
    )

    # ALWAYS render the pristine base chart. No auto-scaling issues here!
    st.plotly_chart(fig, use_container_width=use_container_width, key=f"ml_chart_base_{chart_id}")

    # ── The popover button — CSS makes it hidden by default,
    #    and visible only when hovering the chart wrapper ──────────
    with st.popover("🤖", use_container_width=False):
        st.markdown(f"##### 🤖 ML Insight — {label or chart_id}")

        cols = st.columns(3 if hl_result else 2)

        with cols[0]:
            if st.button("💡 Insight", key=f"ml_i_{chart_id}", use_container_width=True):
                def _img_provider(cid: str) -> bytes | None:
                    if not can_export:
                        return None
                    f = st.session_state["ml_chart_figures"].get(cid)
                    if f is None:
                        return None
                    try:
                        return figure_to_png_bytes(f)
                    except Exception:
                        return None

                with st.spinner("Đang tạo insight..."):
                    try:
                        result = plugin.generate_insight(
                            chart_id=chart_id,
                            dataframe=df,
                            filter_context=filter_context or {},
                            include_image=False, # Removed image sending as requested
                            image_provider=_img_provider,
                        )
                        st.session_state["ml_insight_results"][chart_id] = result
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Insight thất bại: {exc}")

        with cols[1]:
            btn_label = "👀 Xem Highlight" if hl_result else "🎨 Highlight"
            if st.button(btn_label, key=f"ml_h_{chart_id}", use_container_width=True):
                if hl_result:
                    show_highlight_dialog(chart_id, fig, hl_result)
                else:
                    with st.spinner("Đang phân tích biểu đồ..."):
                        try:
                            img_bytes = None
                            if can_export:
                                try:
                                    img_bytes = figure_to_png_bytes(fig)
                                except Exception:
                                    pass
                            hl = plugin.highlight(
                                chart_id=chart_id,
                                figure=fig,
                                title=label or chart_id,
                                include_image=bool(img_bytes),
                                image_bytes=img_bytes,
                            )
                            st.session_state["ml_highlight_results"][chart_id] = hl
                            show_highlight_dialog(chart_id, fig, hl)
                        except Exception as exc:
                            st.error(f"Highlight thất bại: {exc}")

        if hl_result:
            with cols[2]:
                if st.button("🗑️ Xóa", key=f"ml_c_{chart_id}", use_container_width=True):
                    st.session_state["ml_highlight_results"].pop(chart_id, None)
                    st.rerun()

        # ── Show insight result ──────────────────────────────────
        insight = st.session_state["ml_insight_results"].get(chart_id)
        if insight:
            st.markdown(f"### {insight.headline}")
            for item in insight.insights:
                st.markdown(f"- {item}")
            if insight.warnings:
                # Filter out the internal 'unknown evidence keys' warning to avoid confusing the user
                filtered_warnings = [w for w in insight.warnings if "Insight referenced unknown evidence keys" not in w]
                if filtered_warnings:
                    st.warning(" | ".join(filtered_warnings))
            if insight.limitations:
                st.caption("⚠️ " + " | ".join(insight.limitations))


# ---------------------------------------------------------------------------
# Public API: Chat / Ask section (for overview tab)
# ---------------------------------------------------------------------------

def render_chat_section(df: pd.DataFrame) -> None:
    """Render the Chat with AI section — for asking questions about the data.

    This integrates the ``plugin.ask()`` functionality from the demo.
    Renders a chat input + tag selector + response area.
    """
    _init_ml_state()
    can_export = _check_image_export()
    plugin = get_plugin()

    st.markdown(
        "<div class='ml-chat-section'>"
        "<div class='ml-chat-header'>"
        "<span class='ml-chat-icon'>🤖</span>"
        "<span class='ml-chat-title'>Hỏi đáp AI về dữ liệu</span>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Tag scope selector ───────────────────────────────────────
    all_chart_ids = plugin.list_chart_ids()
    all_tab_ids = plugin.list_tab_ids()

    tag_options: list[str] = []
    tag_labels: dict[str, str] = {}
    for cid in all_chart_ids:
        tag = f"#{cid}"
        tag_options.append(tag)
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
    tag_labels["#all"] = "🌐 Tất cả biểu đồ"

    col_tags, col_q, col_btn = st.columns([3, 5, 2], vertical_alignment="bottom")

    with col_tags:
        selected_tags = st.multiselect(
            "Phạm vi",
            options=tag_options,
            format_func=lambda t: tag_labels.get(t, t),
            default=[],
            key="ml_chat_tags",
            placeholder="Chọn biểu đồ hoặc tab...",
        )

    with col_q:
        question = st.text_area(
            "Câu hỏi",
            value="",
            key="ml_chat_question",
            height=68,
            placeholder="VD: Tóm tắt xu hướng doanh số và đưa bằng chứng...\n(Shift+Enter để xuống dòng)",
        )

    with col_btn:
        ask_clicked = st.button(
            "🚀 Hỏi AI",
            key="ml_chat_ask",
            use_container_width=True,
            disabled=not bool(question and question.strip()),
        )

    # ── Resolve scope ────────────────────────────────────────────
    parsed = plugin.parse_question_tags(question) if question else None
    final_question = (parsed.cleaned_question if parsed else question) or question

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
    final_chart_ids = list(dict.fromkeys(
        chip_chart_ids + (parsed.chart_ids if parsed else [])
    ))
    final_tab_id = chip_tab_id or (parsed.tab_id if parsed else None)

    if use_all:
        final_chart_ids = []
        final_tab_id = None

    # ── Image provider ───────────────────────────────────────────
    def _chat_image_provider(chart_id: str) -> bytes | None:
        if not can_export:
            return None
        fig = st.session_state.get("ml_chart_figures", {}).get(chart_id)
        if fig is None:
            return None
        try:
            return figure_to_png_bytes(fig)
        except Exception:
            return None

    if ask_clicked and question and question.strip():
        # Inject CSS to block the UI while loading
        st.markdown(
            """
            <style>
            .stSpinner {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 99999;
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.spinner("🤖 Đang phân tích dữ liệu, vui lòng chờ..."):
            try:
                answer = plugin.ask(
                    question=final_question,
                    dataframe=df,
                    chart_ids=final_chart_ids if final_chart_ids else None,
                    tab_id=final_tab_id,
                    include_images=False,
                    image_provider=_chat_image_provider,
                )
                st.session_state["ml_chat_answer"] = answer
            except Exception as e:
                st.error(f"❌ Có lỗi xảy ra khi hỏi AI: {e}")

    # ── Show answer ──────────────────────────────────────────────
    answer = st.session_state.get("ml_chat_answer")
    if answer:
        st.markdown(
            f"<div class='ml-chat-answer'>"
            f"<div class='ml-chat-answer-label'>🤖 Trả lời</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(answer.answer)
        if answer.evidence_table:
            st.dataframe(pd.DataFrame(answer.evidence_table), use_container_width=True)
        if answer.limitations:
            st.caption("⚠️ " + " · ".join(answer.limitations))
        if answer.warnings:
            st.warning(" | ".join(answer.warnings))
        for attachment in answer.attachments:
            st.download_button(
                label=f"📥 {attachment.filename}",
                data=attachment.content,
                file_name=attachment.filename,
                mime=attachment.mime_type,
                key=f"ml_dl_{attachment.chart_id}",
            )
