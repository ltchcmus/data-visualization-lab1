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


def _q7_bubble_chart(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    needed = {"rating_average", "review_count", "all_time_quantity_sold"}
    if not needed.issubset(sold_df.columns):
        st.info("Thiếu cột rating_average hoặc review_count.")
        return

    review = pd.to_numeric(sold_df["review_count"], errors="coerce")
    rating = pd.to_numeric(sold_df["rating_average"], errors="coerce")
    valid = sold_df[review.notna() & rating.notna() & (review > 0)].copy()
    valid["review_count"] = review[review.notna() & rating.notna() & (review > 0)].values
    valid["rating_average"] = rating[review.notna() & rating.notna() & (review > 0)].values

    review_cap = float(valid["review_count"].quantile(0.95))
    valid["review_count"] = valid["review_count"].clip(upper=review_cap)

    fig = px.scatter(
        valid,
        x="rating_average",
        y="review_count",
        size="all_time_quantity_sold",
        color="all_time_quantity_sold",
        color_continuous_scale=[[0, colors[0]], [0.5, colors[2]], [1, colors[1]]],
        log_y=True,
        opacity=0.6,
        size_max=35,
        labels={
            "rating_average": "Điểm rating",
            "review_count": "Số lượt đánh giá (log)",
            "all_time_quantity_sold": "Lượng bán",
        },
        title="Q7 — Rating × Review → Doanh số (Bubble Chart)",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar={"title": "Lượng bán"},
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Kích thước bong bóng tỉ lệ với **lượng bán** — bong bóng lớn ở góc trên phải = sách vừa được đánh giá cao vừa có nhiều review → doanh số tốt nhất.
- Review count thường có tương quan mạnh hơn với doanh số so với rating vì nó phản ánh **lượng người đã mua thực tế**.
- Sách có rating cao nhưng ít review có thể là sách mới hoặc niche — tiềm năng nếu được quảng bá thêm.
"""
        )


def _q7_correlation_heatmap(df: pd.DataFrame, heatmap_scale: str) -> None:
    cols = ["price", "discount_rate", "rating_average", "review_count", "all_time_quantity_sold"]
    available = [c for c in cols if c in df.columns]
    if len(available) < 2:
        st.info("Không đủ cột để tính heatmap tương quan.")
        return

    corr = df[available].apply(pd.to_numeric, errors="coerce").corr()

    labels_vn = {
        "price": "Giá",
        "discount_rate": "Discount",
        "rating_average": "Rating",
        "review_count": "Số review",
        "all_time_quantity_sold": "Lượng bán",
    }
    corr.index = [labels_vn.get(c, c) for c in corr.index]
    corr.columns = [labels_vn.get(c, c) for c in corr.columns]

    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale=heatmap_scale,
        zmin=-1,
        zmax=1,
        title="Q7 — Ma trận tương quan các biến số lượng",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Heatmap cho cái nhìn tổng quát về **hướng và độ mạnh** của các mối quan hệ.
- Giá trị gần **+1** = tương quan dương mạnh; gần **-1** = tương quan âm mạnh; gần **0** = ít liên hệ.
- Kết hợp với bubble chart để xác nhận biến nào thực sự "dẫn dắt" doanh số.
"""
        )


def _q8_competitive_advantage(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    
    st.markdown("<h5 style='text-align: center; color: #0f2740; font-weight: bold; margin-bottom: 20px;'>Q8 — Lợi thế cạnh tranh: Nhà phân phối & Freeship</h5>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    c1 = colors[0] if len(colors) > 0 else "#3b82f6"
    c2 = colors[1] if len(colors) > 1 else "#ef4444"
    c_other = "#94a3b8"

    # 1. Donut Chart for Freeship
    if "has_freeship" in sold_df.columns:
        valid_fs = sold_df[sold_df["has_freeship"].notna()].copy()
        valid_fs["freeship_label"] = valid_fs["has_freeship"].map(
            {True: "Có Freeship", False: "Không Freeship", 1: "Có Freeship", 0: "Không Freeship"}
        ).fillna("Không xác định")
        valid_fs = valid_fs[valid_fs["freeship_label"] != "Không xác định"]
        
        fs_counts = valid_fs["freeship_label"].value_counts().reset_index()
        fs_counts.columns = ["freeship_label", "count"]
        
        fig1 = go.Figure(data=[go.Pie(
            labels=fs_counts["freeship_label"], 
            values=fs_counts["count"], 
            hole=.55,
            marker=dict(colors=[c1, c_other]),
            textinfo='percent+label',
            hovertemplate="%{label}<br>Số đầu sách: %{value:,.0f}<extra></extra>"
        )])
        fig1.update_layout(
            title={"text": "Tỷ trọng sách theo Chính sách Freeship", "font": {"size": 14}},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=20, l=20, r=20),
            showlegend=False
        )
        _apply_black_text(fig1)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
    else:
        with col1:
            st.caption("Không có dữ liệu Freeship.")

    # 2. Bar chart for Tiki Trading vs Others
    if "current_seller_name" in sold_df.columns:
        valid_seller = sold_df[sold_df["current_seller_name"].notna()].copy()
        valid_seller["seller_group"] = valid_seller["current_seller_name"].apply(
            lambda x: "Tiki Trading" if "tiki trading" in str(x).lower() else "Nhà bán khác"
        )
        
        seller_agg = valid_seller.groupby("seller_group").agg(
            avg_sold=("all_time_quantity_sold", "mean")
        ).reset_index()
        
        seller_agg = seller_agg.sort_values("avg_sold", ascending=False)
        
        fig2 = go.Figure(data=[go.Bar(
            x=seller_agg["seller_group"],
            y=seller_agg["avg_sold"],
            marker_color=[c2 if g == "Tiki Trading" else c_other for g in seller_agg["seller_group"]],
            text=seller_agg["avg_sold"].apply(lambda x: format_vn(x)),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Lượng bán TB: %{y:,.0f}<extra></extra>"
        )])
        fig2.update_layout(
            title={"text": "Lượng bán TB: Tiki Trading vs Nhà bán khác", "font": {"size": 14}},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=40, b=20, l=20, r=20),
            yaxis_title="Lượng bán trung bình",
            xaxis_title="",
            yaxis_range=[0, seller_agg["avg_sold"].max() * 1.25]
        )
        _apply_black_text(fig2)
        with col2:
            st.plotly_chart(fig2, use_container_width=True)
    else:
        with col2:
            st.caption("Không có dữ liệu Nhà bán.")

    # 3. Combined Grouped Bar chart
    if "has_freeship" in sold_df.columns and "current_seller_name" in sold_df.columns:
        valid_combo = sold_df.dropna(subset=["has_freeship", "current_seller_name"]).copy()
        valid_combo["freeship_label"] = valid_combo["has_freeship"].map(
            {True: "Có Freeship", False: "Không Freeship", 1: "Có Freeship", 0: "Không Freeship"}
        )
        valid_combo["seller_group"] = valid_combo["current_seller_name"].apply(
            lambda x: "Tiki Trading" if "tiki trading" in str(x).lower() else "Nhà bán khác"
        )
        valid_combo = valid_combo[valid_combo["freeship_label"].notna()]
        
        combo_agg = valid_combo.groupby(["seller_group", "freeship_label"]).agg(
            avg_sold=("all_time_quantity_sold", "mean")
        ).reset_index()
        
        fig3 = px.bar(
            combo_agg, 
            x="seller_group", 
            y="avg_sold", 
            color="freeship_label",
            barmode="group",
            color_discrete_sequence=[c1, c_other],
            labels={
                "seller_group": "Nhóm nhà phân phối",
                "avg_sold": "Lượng bán trung bình",
                "freeship_label": "Chính sách"
            },
            title="Tác động kép: Sự kết hợp giữa Nhà phân phối lớn & Freeship"
        )
        fig3.for_each_trace(
            lambda trace: trace.update(
                text=[format_vn(v) for v in trace.y],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Chính sách: %{data.name}<br>Lượng bán TB: %{y:,.0f}<extra></extra>",
            )
        )
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center", yanchor="bottom"),
            margin=dict(t=50, b=20),
            yaxis_range=[0, combo_agg["avg_sold"].max() * 1.25]
        )
        _apply_black_text(fig3)
        st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Nhận xét", icon=":material/insights:"):
        st.markdown(
            """
- **Độ phủ Freeship**: Biểu đồ Donut cho thấy tỷ trọng áp dụng chính sách giao hàng miễn phí trên toàn bộ danh mục sách. Freeship hiện nay là một tiêu chuẩn ngầm giúp kích thích người mua chốt đơn.
- **Sức mạnh của Tiki Trading**: Biểu đồ cột bên phải phản ánh chênh lệch doanh số khổng lồ giữa Tiki Trading và các nhà bán bên thứ 3. Sách do Tiki Trading bán đạt doanh số cao vượt trội nhờ lợi thế về uy tín (100% chính hãng), tốc độ giao hàng (TikiNOW), và các ưu đãi đi kèm.
- **Lợi thế cạnh tranh kép**: Khi kết hợp cả hai yếu tố (Biểu đồ nhóm), dễ dàng thấy một cuốn sách vừa được phân phối bởi Tiki Trading, vừa có Freeship sẽ tạo ra một **hào cản cạnh tranh tuyệt đối** về lượng bán, bỏ xa hoàn toàn các nhà bán nhỏ lẻ không có Freeship.
"""
        )


def render_rating_policy_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown("<div class='tab-page-header'>Tab 4 — Đánh giá & Chính sách</div>", unsafe_allow_html=True)

    rating = pd.to_numeric(df.get("rating_average", pd.Series(dtype=float)), errors="coerce")
    review = pd.to_numeric(df.get("review_count", pd.Series(dtype=float)), errors="coerce")

    avg_rating = float(rating.dropna().mean()) if rating.notna().any() else 0.0
    avg_review = float(review.dropna().mean()) if review.notna().any() else 0.0
    freeship_col = df.get("has_freeship")
    pct_free = 0.0
    if freeship_col is not None:
        pct_free = float(freeship_col.eq(True).sum() / freeship_col.notna().sum() * 100)
    _render_kpi_row(
        [
            ("Rating trung bình", f"{format_vn(avg_rating, 2)} ⭐", "star", "blue"),
            ("Số review TB", format_vn(avg_review), "message", "amber"),
            ("Tỷ lệ có freeship", f"{format_vn(pct_free, 1)}%", "ship", "red"),
        ]
    )

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        _q7_bubble_chart(df, colors)
    with col_b:
        _q7_correlation_heatmap(df, heatmap_scale)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q8_competitive_advantage(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
