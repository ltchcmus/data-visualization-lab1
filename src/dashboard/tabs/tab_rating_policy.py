from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


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
    fig.update_xaxes(title_font={"color": "#000000"}, tickfont={"color": "#000000"})
    fig.update_yaxes(title_font={"color": "#000000"}, tickfont={"color": "#000000"})


def _render_kpi_row(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(
                f"""
                <div style="background:linear-gradient(105deg,#dcedff 0%,#eff6ff 52%,#ffffff 100%);border:1px solid #cfe0f2;border-radius:10px;padding:10px 12px;box-shadow:0 8px 18px rgba(31,79,125,0.12);">
                    <div style="font-size:0.78rem;font-weight:700;color:#173a5e;opacity:0.9;">{label}</div>
                    <div style="margin-top:4px;font-size:1.25rem;font-weight:800;color:#000000;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
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


def _q8_freeship_violin(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "has_freeship" not in sold_df.columns:
        st.info("Không có cột has_freeship.")
        return

    valid = sold_df[sold_df["has_freeship"].notna()].copy()
    valid["freeship_label"] = valid["has_freeship"].map(
        {True: "Có freeship", False: "Không freeship", 1: "Có freeship", 0: "Không freeship"}
    ).fillna("Không xác định")
    valid = valid[valid["freeship_label"] != "Không xác định"]

    fig = px.violin(
        valid,
        x="freeship_label",
        y="all_time_quantity_sold",
        color="freeship_label",
        color_discrete_sequence=[colors[0], colors[1]],
        box=True,
        log_y=True,
        labels={
            "freeship_label": "Chính sách freeship",
            "all_time_quantity_sold": "Lượng bán (log)",
        },
        title="Q8 — Freeship & Doanh số (Violin + Boxplot)",
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    _apply_black_text(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Violin cho thấy **toàn bộ phân phối** — không chỉ trung vị như boxplot thông thường.
- Nếu nhóm "Có freeship" có violin rộng hơn ở phần trên → freeship gắn với sản phẩm bán chạy nhiều hơn.
- Thang log giúp so sánh nhóm có outlier cực lớn mà không bị méo hình dạng violin.
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
            ("Rating trung bình", f"{avg_rating:.2f} ⭐"),
            ("Số review TB", f"{avg_review:,.0f}"),
            ("Tỷ lệ có freeship", f"{pct_free:.1f}%"),
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
    _q8_freeship_violin(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
