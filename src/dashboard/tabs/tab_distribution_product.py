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


def _q1_long_tail(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    fig = px.histogram(
        sold_df,
        x="all_time_quantity_sold",
        nbins=80,
        log_y=True,
        color_discrete_sequence=[colors[0]],
        labels={"all_time_quantity_sold": "Lượng bán (all-time)", "count": "Số đầu sách (log)"},
        title="Q1 — Phân bổ doanh số: Hiệu ứng Long-tail",
    )
    fig.update_layout(
        bargap=0.05,
        xaxis_title="Lượng bán (all-time)",
        yaxis_title="Số đầu sách (thang log)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Phân phối doanh số có dạng **long-tail điển hình**: phần lớn đầu sách bán rất ít, một số ít best-seller chiếm tỷ trọng lớn.
- Trục Y log làm rõ tầng bậc: hàng nghìn sách bán < 10 cuốn, trong khi đỉnh cao nhất có thể đạt hàng chục nghìn.
- Gợi ý chiến lược: tập trung marketing vào nhóm "rising stars" (đang leo lên tail) thay vì cạnh tranh trực tiếp với best-seller.
"""
        )


def _q2_category_boxplot(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    col = "cat_level_3" if "cat_level_3" in sold_df.columns else "cat_level_2"
    if col not in sold_df.columns:
        st.info("Không có cột danh mục để vẽ boxplot.")
        return

    medians = (
        sold_df.groupby(col)["all_time_quantity_sold"]
        .median()
        .sort_values(ascending=False)
    )
    top_cats = medians.head(15).index.tolist()
    plot_df = sold_df[sold_df[col].isin(top_cats)].copy()
    plot_df[col] = pd.Categorical(plot_df[col], categories=top_cats, ordered=True)

    fig = px.box(
        plot_df,
        x=col,
        y="all_time_quantity_sold",
        log_y=True,
        color=col,
        color_discrete_sequence=colors,
        labels={col: "Thể loại", "all_time_quantity_sold": "Lượng bán (log)"},
        title="Q2 — Hiệu quả bán hàng theo thể loại (Top 15)",
    )
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Boxplot sắp xếp theo **median giảm dần** — thể loại đầu tiên có trung vị doanh số cao nhất.
- Độ rộng của box cho thấy tính **ổn định**: box hẹp = bán đều, box rộng = phân tán cao (dễ có best-seller nhưng cũng nhiều sách ế).
- Các điểm ngoài box là **outlier / best-seller** tiềm năng trong từng thể loại.
"""
        )


def _q10_pages_vs_sold(df: pd.DataFrame, colors: list[str]) -> None:
    sold_df = _filter_sold(df)
    if "number_of_page" not in sold_df.columns:
        st.info("Không có cột số trang để vẽ scatter.")
        return

    pages = pd.to_numeric(sold_df["number_of_page"], errors="coerce")
    valid = sold_df[pages.notna() & (pages > 0)].copy()
    valid["number_of_page"] = pages[pages.notna() & (pages > 0)].values

    def _page_group(p: float) -> str:
        if p < 100:
            return "<100 trang"
        if p < 300:
            return "100–300 trang"
        if p < 500:
            return "300–500 trang"
        return ">500 trang"

    valid["page_group"] = valid["number_of_page"].map(_page_group)
    group_order = ["<100 trang", "100–300 trang", "300–500 trang", ">500 trang"]

    fig = px.scatter(
        valid,
        x="number_of_page",
        y="all_time_quantity_sold",
        color="page_group",
        color_discrete_sequence=colors,
        category_orders={"page_group": group_order},
        trendline="ols",
        log_y=True,
        opacity=0.55,
        labels={
            "number_of_page": "Số trang",
            "all_time_quantity_sold": "Lượng bán (log)",
            "page_group": "Nhóm số trang",
        },
        title="Q10 — Độ dày sách vs Doanh số",
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Nhận xét"):
        st.markdown(
            """
- Đường hồi quy OLS cho thấy **chiều hướng tương quan** giữa số trang và doanh số.
- Nhóm sách "100–300 trang" thường có mật độ bán cao nhất — phù hợp với thói quen đọc phổ thông.
- Sách >500 trang có phân tán lớn: một số trở thành best-seller (sách giáo khoa, tiểu thuyết kinh điển), nhưng phần lớn bán ít hơn.
"""
        )


def render_distribution_product_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    st.markdown("### Tab 1 — Phân bổ & Sản phẩm")

    sold_df = _filter_sold(df)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Sách có doanh số > 0", f"{len(sold_df):,}")
    with k2:
        median_sold = int(sold_df["all_time_quantity_sold"].median())
        st.metric("Doanh số trung vị", f"{median_sold:,}")
    with k3:
        top1_pct = (
            sold_df.nlargest(int(len(sold_df) * 0.01), "all_time_quantity_sold")[
                "all_time_quantity_sold"
            ].sum()
            / sold_df["all_time_quantity_sold"].sum()
            * 100
        )
        st.metric("Top 1% sách chiếm", f"{top1_pct:.1f}% doanh số")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        _q1_long_tail(df, colors)
    with col_b:
        _q2_category_boxplot(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    _q10_pages_vs_sold(df, colors)
    st.markdown("</div>", unsafe_allow_html=True)
