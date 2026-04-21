"""
app.py — Book Sales Analytics Dashboard

A modern Streamlit dashboard for analysing Tiki book sales data.
Run:  streamlit run dashboard/app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

# ── Local modules ──
from style import inject_custom_css, get_palette
from filters import sidebar_filters
from charts import (
    discount_chart,
    pareto_chart,
    bubble_chart,
    heatmap_chart,
    violin_chart,
)

# ══════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════

DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "book_dataset_clean_locked_rows_run2.csv"
)


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    """Load and lightly type-cast the pre-processed dataset."""
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

    # Numeric
    num_cols = [
        "price", "list_price", "discount_rate", "rating_average",
        "review_count", "all_time_quantity_sold", "number_of_page", "stock",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Boolean
    bool_cols = ["has_freeship", "is_authentic", "has_return_policy"]
    for c in bool_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.upper().map(
                {"TRUE": True, "FALSE": False, "1": True, "0": False}
            )

    # Derived: revenue
    if "revenue" not in df.columns:
        df["revenue"] = df["price"] * df["all_time_quantity_sold"]

    return df


# ══════════════════════════════════════════════════════════════════
# KPI helpers
# ══════════════════════════════════════════════════════════════════

def _fmt_vnd(value: float) -> str:
    """Format a number as compact VND."""
    if value >= 1e12:
        return f"₫{value / 1e12:,.2f}T"
    if value >= 1e9:
        return f"₫{value / 1e9:,.2f}B"
    if value >= 1e6:
        return f"₫{value / 1e6:,.1f}M"
    return f"₫{value:,.0f}"


def _fmt_int(value: float) -> str:
    if value >= 1e6:
        return f"{value / 1e6:,.2f}M"
    if value >= 1e3:
        return f"{value / 1e3:,.1f}K"
    return f"{value:,.0f}"


def render_kpi_cards(df: pd.DataFrame) -> None:
    """Render a row of styled KPI metric cards."""
    total_revenue = df["revenue"].sum()
    total_sold = df["all_time_quantity_sold"].sum()
    avg_rating = df["rating_average"].mean()
    n_authors = df["authors"].nunique()
    n_sellers = df["current_seller_name"].nunique()
    n_books = len(df)

    with st.container(key="kpi_card"):
        cols = st.columns(6)
        cols[0].metric(":material/payments: Tổng doanh thu", _fmt_vnd(total_revenue))
        cols[1].metric(":material/shopping_cart: Tổng đã bán", _fmt_int(total_sold))
        cols[2].metric(":material/star: Đánh giá TB", f"{avg_rating:.2f} ⭐")
        cols[3].metric(":material/menu_book: Sách", f"{n_books:,}")
        cols[4].metric(":material/person: Tác giả", f"{n_authors:,}")
        cols[5].metric(":material/storefront: Nhà bán", f"{n_sellers:,}")


# ══════════════════════════════════════════════════════════════════
# Top books table
# ══════════════════════════════════════════════════════════════════

def render_top_books(df: pd.DataFrame, n: int = 15) -> None:
    """Show a sortable table of top-selling books."""
    display_cols = ["name", "authors", "price", "revenue", "all_time_quantity_sold",
                    "rating_average", "review_count", "discount_rate"]
    existing = [c for c in display_cols if c in df.columns]
    top = df.nlargest(n, "all_time_quantity_sold")[existing].reset_index(drop=True)
    top.index += 1

    rename = {
        "name": "Tên sách",
        "authors": "Tác giả",
        "price": "Giá (₫)",
        "revenue": "Doanh thu (₫)",
        "all_time_quantity_sold": "Đã bán",
        "rating_average": "Đánh giá",
        "review_count": "Nhận xét",
        "discount_rate": "Giảm giá %",
    }
    top = top.rename(columns=rename)

    st.dataframe(
        top,
        use_container_width=True,
        height=min(35 * len(top) + 40, 560),
        column_config={
            "Giá (₫)": st.column_config.NumberColumn(format="%d"),
            "Doanh thu (₫)": st.column_config.NumberColumn(format="%d"),
            "Đã bán": st.column_config.NumberColumn(format="%d"),
            "Đánh giá": st.column_config.NumberColumn(format="%.1f"),
            "Nhận xét": st.column_config.NumberColumn(format="%d"),
            "Giảm giá %": st.column_config.NumberColumn(format="%d%%"),
        },
    )


# ══════════════════════════════════════════════════════════════════
# Main app
# ══════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="Phân tích doanh số Kinh doanh Sách",
        page_icon=":material/analytics:",
        layout="wide",
    )

    inject_custom_css()

    # ── Load data ──
    if not DATA_PATH.exists():
        st.error(f"Dataset not found at `{DATA_PATH}`")
        st.stop()

    raw_df = load_data(str(DATA_PATH))

    # ── Sidebar: accessibility + filters ──
    st.sidebar.markdown("### :material/accessibility: Trợ năng")
    colorblind = st.sidebar.toggle("Chế độ mù màu", value=False, key="cb_mode")

    if colorblind:
        palette = get_palette(True)
        st.sidebar.caption(
            f"Đang sử dụng bảng màu Okabe-Ito ({len(palette)} màu)"
        )

    filtered_df = sidebar_filters(raw_df)

    # ── Download button (sidebar bottom) ──
    csv_bytes = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.sidebar.download_button(
        label=":material/download: Tải tệp CSV đã lọc",
        data=csv_bytes,
        file_name="book_sales_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # ── Header ──
    st.title("Phân tích doanh số Kinh doanh Sách")
    st.caption(
        "Dashboard tương tác dữ liệu bán sách Tiki — "
        "phân tích chiến lược giảm giá, tác giả hàng đầu, hành vi mua hàng và hiệu suất từ các nhà bán."
    )

    # ── Empty guard ──
    if filtered_df.empty:
        st.warning(
            "Không tìm thấy sách nào phù hợp với bộ lọc. Hãy điều chỉnh bộ lọc ở thanh bên gập.",
            icon=":material/warning:",
        )
        st.stop()

    # ── KPI cards ──
    render_kpi_cards(filtered_df)

    # ══════════════════════════════════════════════════════════════
    # Section 1 — Discount analysis
    # ══════════════════════════════════════════════════════════════
    with st.container():
        st.header(":material/sell: Phân tích giảm giá")
    st.caption(
        "Có tồn tại một ngưỡng giảm giá mà tại đó doanh số tăng mạnh không, "
        "hay mối quan hệ là tuyến tính?"
    )

    st.plotly_chart(
        discount_chart(filtered_df, colorblind),
        use_container_width=True,
        key="chart_discount",
    )

    with st.expander(":material/info: Diễn giải", expanded=False):
        st.markdown(
            "Biểu đồ cột hiển thị **trung bình số lượng bán** theo các mốc giảm giá 5%. "
            "Cột màu vàng/cam nhấn mạnh khoảng giảm giá đạt đỉnh doanh số TB.\n\n"
            "Đường thẳng thể hiện **tổng số lượng bán** trong các khoảng tương ứng. "
            "Một bước nhảy vọt chỉ ra một mức ưu đãi phù hợp để thu hút khách hàng."
        )

    # ══════════════════════════════════════════════════════════════
    # Section 2 — Pareto / 80-20
    # ══════════════════════════════════════════════════════════════
    with st.container(key="section_header"):
        st.header(":material/leaderboard: Phân tích Pareto theo tác giả")
    st.caption("Tác giả nào đang mang lại phần lớn doanh thu? (Quy tắc Pareto 80/20)")

    top_n = st.slider(
        "Top N tác giả",
        min_value=10,
        max_value=50,
        value=20,
        step=5,
        key="pareto_top_n",
    )

    st.plotly_chart(
        pareto_chart(filtered_df, top_n=top_n, colorblind=colorblind),
        use_container_width=True,
        key="chart_pareto",
    )

    with st.expander(":material/info: Diễn giải", expanded=False):
        st.markdown(
            "Biểu đồ cột biểu diễn tổng doanh thu của từng tác giả. "
            "Đường tích lũy cho thấy phần trăm doanh thu mà các tác giả top đầu đóng góp.\n\n"
            "Các tác giả nằm trước **đường đứt khúc 80 %** mang yếu tố cốt lõi — "
            "cần dành sự ưu tiên cho marketing các sản phẩm này."
        )

    # ══════════════════════════════════════════════════════════════
    # Section 3 — Customer behaviour (bubble + heatmap)
    # ══════════════════════════════════════════════════════════════
    with st.container(key="section_header2"):
        st.header(":material/group: Hành vi khách hàng")
    st.caption(
        "Đánh giá và nhận xét ảnh hưởng đến doanh số như thế nào? "
        "Các yếu tố nào tương quan chặt chẽ nhất?"
    )

    col_bubble, col_heat = st.columns([3, 2])

    with col_bubble:
        st.plotly_chart(
            bubble_chart(filtered_df, colorblind),
            use_container_width=True,
            key="chart_bubble",
        )

    with col_heat:
        st.plotly_chart(
            heatmap_chart(filtered_df, colorblind),
            use_container_width=True,
            key="chart_heatmap",
        )

    with st.expander(":material/info: Diễn giải", expanded=False):
        st.markdown(
            "**Biểu đồ bong bóng** — mỗi chấm là một quyển sách. Trục X = Đánh giá sao, Trục Y = Số lượng nhận xét "
            "(thang tuyến tính/log), kích thước = Số tiền đã bán. Những bong bóng lớn phía trên bên phải "
            "cho thấy sách bán cực kỳ chạy với độ uy tín cao.\n\n"
            "**Biểu đồ nhiệt** — Hệ số tương quan Pearson giữa mức giá, tỷ lệ giảm, xếp hạng... "
            "Chỉ số càng gần 1 hoặc -1 càng chứng tỏ mối liên kết tỷ lệ thuận / nghịch mang tính định luật."
        )

    # ══════════════════════════════════════════════════════════════
    # Section 4 — Seller performance
    # ══════════════════════════════════════════════════════════════
    with st.container(key="section_header3"):
        st.header(":material/local_shipping: Hiệu suất nhà bán")
    st.caption("Các nhà bán lớn hay khuyến mãi freeship có tạo ra lợi thế cạnh tranh doanh số không?")

    tab_free, tab_seller = st.tabs([
        ":material/local_shipping: So sánh Freeship",
        ":material/storefront: Top nhà bán hàng",
    ])

    with tab_free:
        st.plotly_chart(
            violin_chart(filtered_df, mode="freeship", colorblind=colorblind),
            use_container_width=True,
            key="chart_violin_freeship",
        )

    with tab_seller:
        st.plotly_chart(
            violin_chart(filtered_df, mode="seller", colorblind=colorblind),
            use_container_width=True,
            key="chart_violin_seller",
        )

    with st.expander(":material/info: Diễn giải", expanded=False):
        st.markdown(
            "Biểu đồ Violin hiển thị **sự phân bố doanh số** thông qua log₁₀(số lượng bán) "
            "cho mỗi nhóm. Chỗ nào phình to ra có nghĩa là mật độ sách ở mức doanh số đó cực kỳ dày đặc.\n\n"
            "Hộp vuông nhỏ phía trong thể hiện mức trung vị (Median) & phạm vi IQR. Trung vị ở mức biểu đồ trên cao "
            "gợi ý rằng nhóm đó liên tục bán ưu việt hơn so với nhóm còn lại."
        )

    # ══════════════════════════════════════════════════════════════
    # Bonus — Top books table
    # ══════════════════════════════════════════════════════════════
    with st.container(key="section_header4"):
        st.header(":material/format_list_numbered: Top sách bán chạy")

    render_top_books(filtered_df, n=20)


# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
