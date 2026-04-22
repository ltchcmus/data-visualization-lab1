from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..format_utils import format_vn
from ..ui_cards import render_metric_strip


def _filter_sold(df: pd.DataFrame) -> pd.DataFrame:
    sold = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    mask = sold > 0
    sub = df[mask].copy()
    cap = sold[mask].quantile(0.99)
    sub["all_time_quantity_sold"] = sold[mask].clip(upper=cap).values
    return sub


def _apply_black_text(fig) -> None:
    fig.update_layout(
        font={"color": "#000000"},
        title={"font": {"color": "#000000"}},
    )
    fig.update_xaxes(
        title_font={"color": "#000000"},
        tickfont={"color": "#000000"},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )
    fig.update_yaxes(
        title_font={"color": "#000000"},
        tickfont={"color": "#000000"},
        showgrid=True,
        gridcolor="#e7edf5",
        zerolinecolor="#dbe7f2",
        linecolor="#dbe7f2",
    )


def _render_kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    render_metric_strip(
        [
            {"label": label, "value": value, "icon": icon, "tone": tone}
            for label, value, icon, tone in items
        ],
        compact=True,
    )


def _q3_top_publishers(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "publisher_vn" not in sold_df.columns:
        st.caption("Không có cột publisher_vn.")
        return

    pub_agg = (
        sold_df.groupby("publisher_vn")
        .agg(avg_sold=("all_time_quantity_sold", "mean"), book_count=("all_time_quantity_sold", "size"))
        .reset_index()
    )
    pub_agg = pub_agg[pub_agg["book_count"] >= 5].sort_values("avg_sold", ascending=True).tail(15)

    overall_avg = float(sold_df["all_time_quantity_sold"].mean())

    fig = px.bar(
        pub_agg,
        x="avg_sold",
        y="publisher_vn",
        orientation="h",
        color="avg_sold",
        color_continuous_scale=[[0, colors[0]], [1, colors[1]]],
        labels={"avg_sold": "Lượng bán trung bình", "publisher_vn": "Nhà xuất bản"},
        title="Top 15 NXB theo doanh số trung bình (≥5 đầu sách)",
        text=pub_agg["avg_sold"].apply(lambda x: format_vn(x)),
    )
    fig.update_traces(texttemplate="%{text}", textposition="outside")
    fig.update_layout(
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis={"categoryorder": "total ascending"},
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét", icon=":material/analytics:"):
        st.markdown(
            """
- Chỉ lấy NXB có **≥5 đầu sách** để tránh bias từ NXB có 1–2 cuốn may mắn bán chạy.
- NXB dẫn đầu thường là đơn vị lớn có hệ thống phân phối, marketing, hoặc tập trung vào thể loại hot (sách giáo dục, self-help).
"""
        )


def _q4_author_pareto(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "authors" not in sold_df.columns:
        st.caption("Không có cột authors.")
        return

    if "price" in sold_df.columns:
        price = pd.to_numeric(sold_df["price"], errors="coerce").fillna(0)
        sold_df["revenue"] = price * sold_df["all_time_quantity_sold"]
    else:
        sold_df["revenue"] = sold_df["all_time_quantity_sold"]

    def _clean(x):
        if pd.isna(x): return "Ẩn danh"
        s = str(x).strip()
        if s in ["", ".", ",", "-", "Unknown"]: return "Ẩn danh"
        if s.lower() in ["nhiều tác giả", "nhiều tac gia"]: return "Nhiều tác giả"
        return s

    sold_df["authors"] = sold_df["authors"].apply(_clean)

    author_agg = (
        sold_df.groupby("authors")["all_time_quantity_sold"]
        .sum()
        .reset_index()
        .sort_values("all_time_quantity_sold", ascending=False)
        .head(30)
    )
    author_agg["cumulative_pct"] = (
        author_agg["all_time_quantity_sold"].cumsum()
        / author_agg["all_time_quantity_sold"].sum()
        * 100
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=author_agg["authors"],
            y=author_agg["all_time_quantity_sold"],
            name="Tổng lượng bán",
            marker_color=colors[0],
            opacity=0.85,
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=author_agg["authors"],
            y=author_agg["cumulative_pct"],
            name="% tích lũy",
            mode="lines+markers",
            line={"color": colors[1], "width": 2},
            marker={"size": 6},
            yaxis="y2",
        )
    )
    fig.add_hline(
        y=80,
        line_dash="dot",
        line_color="red",
        annotation_text="80%",
        annotation_position="right",
        yref="y2",
    )
    fig.update_layout(
        title="Biểu đồ Pareto: Tác giả & doanh số (top 30)",
        xaxis={"tickangle": -45},
        yaxis={"title": "Tổng lượng bán"},
        yaxis2={"title": "% tích lũy", "overlaying": "y", "side": "right", "range": [0, 105]},
        legend={"orientation": "h", "y": 1.15, "x": 0.5, "xanchor": "center", "yanchor": "bottom"},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=50, b=80),
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét", icon=":material/analytics:"):
        st.markdown(
            """
- Đường tích lũy qua ngưỡng **80%** cho thấy cần bao nhiêu tác giả hàng đầu để chiếm 80% tổng doanh số.
- Nếu đường cắt 80% sớm (ít tác giả) → thị trường **tập trung cao** — rủi ro nếu tác giả đó ngừng hoạt động.
- Tác giả có cột bar cao nhưng không phải 1 đầu sách duy nhất → "bán đều tay" trên nhiều tựa.
"""
        )

def _q4_top_books(df: pd.DataFrame, colors: list[str]) -> None:
    sold_col = pd.to_numeric(df["all_time_quantity_sold"], errors="coerce")
    valid_df = df[sold_col > 0].copy()
    valid_df["quantity"] = pd.to_numeric(valid_df["all_time_quantity_sold"], errors="coerce")
    
    title_col = next((col for col in ["name", "title", "product_name", "book_name"] if col in df.columns), None)
    if "authors" not in valid_df.columns or not title_col:
        st.caption("Không có cột authors hoặc cột tên sách để hiển thị chi tiết.")
        return
        
    def _clean(x):
        if pd.isna(x): return "Ẩn danh"
        s = str(x).strip()
        if s in ["", ".", ",", "-", "Unknown"]: return "Ẩn danh"
        if s.lower() in ["nhiều tác giả", "nhiều tac gia"]: return "Nhiều tác giả"
        return s

    valid_df["authors"] = valid_df["authors"].apply(_clean)
        
    top_books = valid_df.sort_values("quantity", ascending=False).head(15).copy()
    
    # Rút gọn tên sách để trục Y không bị quá dài
    top_books["short_title"] = top_books[title_col].astype(str).apply(lambda x: x[:45] + "..." if len(x) > 45 else x)
    # Chèn ký tự tàng hình (zero-width non-joiner) để đảm bảo tên sách là duy nhất (không bị Plotly gộp)
    top_books["short_title"] = [f"{t}{chr(8204)*i}" for i, t in enumerate(top_books["short_title"])]
    
    # Đưa tên tác giả và lượng bán vào bên trong thanh Bar
    top_books["bar_text"] = (
        "✍️ <b>"
        + top_books["authors"]
        + "</b> &nbsp;|&nbsp; "
        + top_books["quantity"].apply(lambda x: format_vn(x))
    )
    
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=top_books["short_title"],
            x=top_books["quantity"],
            orientation="h",
            marker_color=colors[0] if colors else "#3b82f6",
            text=top_books["bar_text"],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color="#0f2740"),
            customdata=top_books["authors"],
            hovertemplate="<b>%{y}</b><br>Tác giả: %{customdata}<br>Lượng bán: %{x:,.0f}<extra></extra>"
        )
    )
    fig.update_layout(
        title="Top 15 tác phẩm bán chạy nhất & Tác giả tương ứng",
        yaxis={"categoryorder": "total ascending", "title": ""},
        xaxis={"title": "Lượng bán (không loại trừ outlier)"},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=40, t=50, b=10)
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét", icon=":material/insights:"):
        st.markdown(
            """
- Biểu đồ này chỉ ra chính xác các **"siêu phẩm" (blockbusters)** đang dẫn đầu doanh số của toàn hệ thống.
- **Phân tích kết hợp**: Bằng cách đối chiếu các tác giả ở đây với biểu đồ Pareto bên trên, bạn có thể thấy rõ tác giả nào lọt top Pareto nhờ 1-2 siêu phẩm ở đây, và tác giả nào không hề có siêu phẩm nhưng vẫn lọt top nhờ danh mục sách khổng lồ bán đều đặn (ổn định).
"""
        )

def render_publisher_author_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown("<div class='tab-page-header'>Tab 3 — NXB & Tác giả</div>", unsafe_allow_html=True)

    sold_df = _filter_sold(df)
    n_pub = int(df["publisher_vn"].nunique()) if "publisher_vn" in df.columns else 0
    n_authors = int(df["authors"].nunique()) if "authors" in df.columns else 0
    avg_sold = float(sold_df["all_time_quantity_sold"].mean())
    _render_kpi_row(
        [
            ("Số NXB", format_vn(n_pub), "building", "blue"),
            ("Số tác giả", format_vn(n_authors), "users", "amber"),
            ("Doanh số TB", format_vn(avg_sold, 0), "chart", "red"),
        ]
    )

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q3_top_publishers(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q4_author_pareto(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q4_top_books(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
