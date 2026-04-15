import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "data" / "processed" / "book_dataset_clean.csv"

_BLUE   = "#1264A3"
_ORANGE = "#F07D00"

NORMAL_COLORS = [_BLUE, _ORANGE, "#5BA3D9", "#F5A833", "#0A4A7A", "#C06000", "#2E86AB"]
CB_COLORS     = ["#0077BB", "#EE7733", "#009988", "#CC3311", "#33BBEE", "#EE3377", "#BBBBBB"]

# Màu nền cho các KPI card (mỗi card 1 màu riêng)
KPI_COLORS = ["#1264A3", "#009688", "#F07D00", "#7B1FA2",
              "#E53935", "#00796B", "#0288D1", "#558B2F"]

GENRE_MAP = {
    "sach-van-hoc":                     "Văn học",
    "fiction-literature":               "Văn học (EN)",
    "children-books":                   "Sách thiếu nhi",
    "education-teaching":               "Giáo dục",
    "self-help":                        "Kỹ năng sống",
    "business-economics":               "Kinh doanh",
    "art-photography":                  "Nghệ thuật",
    "reference":                        "Tham khảo",
    "history-politics-social-sciences": "Lịch sử / XH",
    "biographies-memoirs":              "Tiểu sử",
    "science-technology":               "Khoa học / CN",
}

TOP_N = 10


# ── HELPERS ───────────────────────────────────────────────────────────────────
def fmt_vnd(value: float) -> str:
    return f"{value:,.0f} VND".replace(",", ".")


def kpi_card(col, label: str, value: str, color: str, icon: str = "", delta: str = ""):
    """Render a colored KPI metric card vào một Streamlit column."""
    delta_html = (
        f'<div style="font-size:0.70rem;margin-top:0.25rem;opacity:0.90;">{delta}</div>'
        if delta else ""
    )
    col.markdown(
        f"""
        <div style="
            background:{color};
            border-radius:10px;
            padding:0.85rem 1rem;
            color:#fff;
            min-height:88px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            box-shadow:0 3px 10px rgba(0,0,0,0.18);
        ">
            <div style="font-size:0.74rem;opacity:0.88;margin-bottom:0.2rem;font-weight:500;">{icon}&nbsp;{label}</div>
            <div style="font-size:1.4rem;font-weight:700;line-height:1.15;">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── DATA ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["category"] = df["cat1"].map({
        "sach-truyen-tieng-viet": "Sách Tiếng Việt",
        "sach-tieng-anh":         "Sách Tiếng Anh",
    })
    df["genre"] = df["cat2"].map(GENRE_MAP).fillna("Khác")
    return df


# ── DRILL-DOWN FILTER ─────────────────────────────────────────────────────────
def render_drill_down_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bộ lọc 3 cấp: Loại sách → Thể loại → Nhà xuất bản.
    Mỗi cấp phụ thuộc vào cấp trước (drill-down).
    Trả về DataFrame đã lọc.
    """
    f1, f2, f3 = st.columns(3)

    # Cấp 1 — Loại sách
    cat_opts = ["Tất cả"] + sorted(df["category"].dropna().unique().tolist())
    with f1:
        cat_sel = st.selectbox(
            "📂 Loại sách",
            cat_opts,
            key="dd_cat",
            help="Chọn loại sách (Tiếng Việt / Tiếng Anh)",
        )

    dff = df if cat_sel == "Tất cả" else df[df["category"] == cat_sel]

    # Cấp 2 — Thể loại (phụ thuộc cấp 1)
    genre_opts = ["Tất cả"] + sorted(dff["genre"].dropna().unique().tolist())
    with f2:
        genre_sel = st.selectbox(
            "📚 Thể loại",
            genre_opts,
            key="dd_genre",
            help="Danh sách thể loại thay đổi theo Loại sách đã chọn",
        )

    if genre_sel != "Tất cả":
        dff = dff[dff["genre"] == genre_sel]

    # Cấp 3 — Nhà xuất bản (phụ thuộc cấp 1 + 2); lấy top 60 theo số lượng
    top_pubs = (
        dff["publisher_vn"]
        .dropna()
        .value_counts()
        .head(60)
        .index.tolist()
    )
    pub_opts = ["Tất cả"] + sorted(top_pubs)
    with f3:
        pub_sel = st.selectbox(
            "🏢 Nhà xuất bản",
            pub_opts,
            key="dd_pub",
            help="Danh sách NXB thay đổi theo Thể loại đã chọn (top 60)",
        )

    if pub_sel != "Tất cả":
        dff = dff[dff["publisher_vn"] == pub_sel]

    # Breadcrumb hiển thị bộ lọc đang áp dụng
    active = [(icon, val) for icon, val in [("📂", cat_sel), ("📚", genre_sel), ("🏢", pub_sel)] if val != "Tất cả"]
    if active:
        crumb_str = "  ›  ".join(f"{i} **{v}**" for i, v in active)
        st.caption(f"🔍 Đang lọc: {crumb_str} &nbsp;|&nbsp; **{len(dff):,}** sản phẩm")
    else:
        st.caption(f"🔍 Đang xem: **Tất cả** &nbsp;|&nbsp; **{len(dff):,}** sản phẩm")

    return dff


# ── TAB: Tổng quan ────────────────────────────────────────────────────────────
def render_overview_tab(df: pd.DataFrame, colors: list):
    if df.empty:
        st.warning("Không có dữ liệu cho bộ lọc đã chọn.")
        return

    # KPI cards
    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "Tổng sản phẩm",  f"{len(df):,}",
             KPI_COLORS[0], "📦")
    kpi_card(k2, "Tổng lượt bán",  f"{df['all_time_quantity_sold'].sum():,.0f}",
             KPI_COLORS[1], "🛒")
    kpi_card(k3, "Giá trung bình", fmt_vnd(df["price"].mean()),
             KPI_COLORS[2], "💰")
    kpi_card(k4, "Số danh mục",    f"{df['genre'].nunique()}",
             KPI_COLORS[3], "📂")

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    # Biểu đồ thanh: Phân bố sản phẩm theo danh mục
    with c1:
        st.subheader("Phân bố sản phẩm theo danh mục")
        genre_counts = df["genre"].value_counts().reset_index()
        genre_counts.columns = ["genre", "count"]
        other_mask = genre_counts["genre"] == "Khác"
        genre_counts = pd.concat(
            [genre_counts[other_mask], genre_counts[~other_mask].sort_values("count")],
            ignore_index=True,
        )
        total = genre_counts["count"].sum()
        top_genre = genre_counts.iloc[-1]
        top_pct = top_genre["count"] / total * 100

        fig1 = px.bar(
            genre_counts, x="count", y="genre", orientation="h",
            color_discrete_sequence=[colors[0]],
            labels={"count": "Số sản phẩm", "genre": "Danh mục"},
            text="count",
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(
            height=400, margin=dict(t=20, r=100, b=40), showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.caption(
            f"💡 **Nhận xét:** Danh mục **{top_genre['genre']}** chiếm tỷ lệ lớn nhất "
            f"({top_pct:.0f}% tổng sản phẩm)."
        )

    # Histogram: Phân phối giá
    with c2:
        st.subheader("Phân phối giá sản phẩm")
        price_cap = int(df["price"].quantile(0.95)) if len(df) > 1 else int(df["price"].max())
        price_cap = max(price_cap, 10_000)
        price_range = st.slider(
            "Khoảng giá (VND)", 0, price_cap, (0, price_cap),
            step=10_000, key="ov_price_rng", format="%d",
        )
        dff2 = df[(df["price"] >= price_range[0]) & (df["price"] <= price_range[1])]

        fig2 = px.histogram(
            dff2, x="price", color="category",
            color_discrete_sequence=colors[:2],
            nbins=30, opacity=0.65, barmode="overlay",
            labels={"price": "Giá (VND)", "count": "Số sản phẩm", "category": "Loại sách"},
        )
        fig2.update_xaxes(tickformat=",.0f", ticksuffix=" VND", nticks=6)
        fig2.update_yaxes(title_text="Số sản phẩm")
        fig2.update_layout(
            height=400, margin=dict(t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)
        median_price = dff2["price"].median() if not dff2.empty else 0
        st.caption(
            f"💡 **Nhận xét:** Giá trung vị **{fmt_vnd(median_price)}**. "
            f"Phần lớn sản phẩm tập trung ở phân khúc giá thấp."
        )

    st.divider()

    # Top 10 sản phẩm
    st.subheader("Top 10 sản phẩm bán chạy nhất")
    rank_by = st.selectbox("Xếp hạng theo", ["Lượt bán", "Đánh giá", "Giá"], key="ov_rank_by")
    col_map = {
        "Lượt bán": ("all_time_quantity_sold", "Lượt bán"),
        "Đánh giá": ("rating_average",         "Điểm đánh giá"),
        "Giá":      ("price",                  "Giá (VND)"),
    }
    col, label = col_map[rank_by]
    top10 = df.nlargest(TOP_N, col)[["name", col]].copy()
    top10["name"] = top10["name"].str[:55]
    top10 = top10.sort_values(col)

    fig3 = px.bar(
        top10, x=col, y="name", orientation="h",
        color_discrete_sequence=[colors[2]],
        labels={col: label, "name": "Sản phẩm"},
        text=col,
    )
    fmt = ",.0f" if col != "rating_average" else ".2f"
    fig3.update_traces(texttemplate=f"%{{text:{fmt}}}", textposition="outside")
    fig3.update_layout(
        height=340, margin=dict(t=20, r=100), showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig3, use_container_width=True)


# ── TAB: Phân tích Giá & Discount ────────────────────────────────────────────
def render_price_tab(df: pd.DataFrame, colors: list):
    if df.empty:
        st.warning("Không có dữ liệu cho bộ lọc đã chọn.")
        return

    pct_disc  = (df["discount_rate"] > 0).mean() * 100
    price_p99 = df["price"].quantile(0.99)

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "Giá trung bình",      fmt_vnd(df["price"].mean()),          KPI_COLORS[0], "💰")
    kpi_card(k2, "Discount trung bình", f"{df['discount_rate'].mean():.1f}%", KPI_COLORS[4], "🏷️")
    kpi_card(k3, "Có giảm giá",         f"{pct_disc:.0f}%",                   KPI_COLORS[5], "✅", "trong tổng số sách")
    kpi_card(k4, "Giá cao nhất (P99)",  fmt_vnd(price_p99),                   KPI_COLORS[6], "📈")

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.subheader("Phân phối giá theo thể loại")
        cap = df["price"].quantile(0.99)
        dff = df[df["price"] <= cap]
        order = (
            dff.groupby("genre")["price"].median()
            .sort_values().index.tolist()
        )
        fig1 = px.box(
            dff, x="price", y="genre",
            category_orders={"genre": order},
            color_discrete_sequence=[colors[0]],
            labels={"price": "Giá (VND)", "genre": "Thể loại"},
        )
        fig1.update_xaxes(tickformat=",.0f", ticksuffix=" VND")
        fig1.update_layout(
            height=340, margin=dict(t=20),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.subheader("Phân bố tỷ lệ giảm giá")
        col_chk, col_mode2 = st.columns([2, 1])
        with col_chk:
            only_disc = st.checkbox("Chỉ sách có giảm giá (> 0%)", value=False, key="pr_only_disc")
        with col_mode2:
            disc_barmode = st.radio("Kiểu", ["Chồng", "Nhóm"], key="pr_disc_mode", horizontal=False)
        dff2 = df[df["discount_rate"] > 0] if only_disc else df
        fig2 = px.histogram(
            dff2, x="discount_rate", color="category",
            color_discrete_sequence=colors[:2],
            nbins=30,
            opacity=0.75 if disc_barmode == "Chồng" else 1.0,
            barmode="overlay" if disc_barmode == "Chồng" else "group",
            labels={"discount_rate": "Giảm giá (%)", "count": "Số sản phẩm", "category": "Loại sách"},
        )
        fig2.update_yaxes(title_text="Số sản phẩm")
        fig2.update_layout(
            height=340, margin=dict(t=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # Box plot: phân bố doanh số theo khoảng giảm giá
    st.subheader("Phân bố số lượng bán theo khoảng giảm giá")
    sold_df = df[(df["all_time_quantity_sold"] > 0) & (df["discount_rate"] > 0)].copy()
    if sold_df.empty:
        st.info("Không có dữ liệu bán hàng có giảm giá trong bộ lọc hiện tại.")
    else:
        sold_cap = sold_df["all_time_quantity_sold"].quantile(0.99)
        sold_df  = sold_df[sold_df["all_time_quantity_sold"] <= sold_cap]
        disc_bins   = [0, 10, 20, 30, 40, 50, 101]
        disc_labels = ["0–10%", "10–20%", "20–30%", "30–40%", "40–50%", "50%+"]
        sold_df["discount_bin"] = pd.cut(
            sold_df["discount_rate"], bins=disc_bins, labels=disc_labels, right=False
        )
        sold_df = sold_df.dropna(subset=["discount_bin"])
        bin_colors = ["#440154", "#31688E", "#26828E", "#1F9E89", "#35B779", "#6ECE58"]
        fig3 = px.box(
            sold_df, x="discount_bin", y="all_time_quantity_sold", color="discount_bin",
            color_discrete_sequence=bin_colors, points="outliers",
            category_orders={"discount_bin": disc_labels},
            labels={"discount_bin": "Khoảng giảm giá (%)", "all_time_quantity_sold": "Số lượng bán"},
            hover_data=["name", "genre", "price"],
        )
        fig3.update_traces(marker=dict(opacity=0.25, size=4))
        fig3.update_layout(
            height=340, margin=dict(t=20), showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("💡 **Nhận xét:** Sách giảm giá cao (30–50%) không nhất thiết bán được nhiều hơn — outlier mới là yếu tố quyết định.")

    st.divider()

    # Scatter: Discount vs Doanh số
    st.subheader("Tương quan giảm giá và doanh số")
    f1, f2, f3 = st.columns([3, 2, 1])
    with f1:
        genres_all = sorted(df["genre"].unique().tolist())
        genre_sel  = st.multiselect(
            "Lọc thể loại", genres_all, default=[],
            placeholder="Tất cả thể loại", key="pr_genre_sel",
        )
    with f2:
        disc_range = st.slider("Giảm giá (%)", 0, 83, (0, 83), key="pr_disc_rng")
    with f3:
        show_trend = st.checkbox("Xu hướng OLS", value=True, key="pr_trend")

    scatter_df = df[df["all_time_quantity_sold"] > 0].copy()
    if not scatter_df.empty:
        scatter_cap = scatter_df["all_time_quantity_sold"].quantile(0.99)
        scatter_df  = scatter_df[scatter_df["all_time_quantity_sold"] <= scatter_cap]
    scatter_df = scatter_df[
        (scatter_df["discount_rate"] >= disc_range[0])
        & (scatter_df["discount_rate"] <= disc_range[1])
    ]
    if genre_sel:
        scatter_df = scatter_df[scatter_df["genre"].isin(genre_sel)]

    if scatter_df.empty:
        st.info("Không có dữ liệu phù hợp với bộ lọc scatter.")
    else:
        fig4 = px.scatter(
            scatter_df, x="discount_rate", y="all_time_quantity_sold", color="category",
            color_discrete_sequence=colors[:2], opacity=0.45,
            trendline="ols" if show_trend else None,
            labels={
                "discount_rate":            "Giảm giá (%)",
                "all_time_quantity_sold":   "Lượt bán",
                "category":                 "Loại sách",
            },
            hover_data=["name", "genre", "price"],
        )
        fig4.update_layout(
            height=340, margin=dict(t=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Tiki Books Dashboard",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    _HEADER_H = "3.2rem"

    st.markdown(
        f"""
        <style>
        /* ── Ẩn hoàn toàn sidebar ── */
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        button[kind="header"] {{
            display: none !important;
        }}

        /* ── Nền trang xanh nhạt ── */
        .stApp {{ background-color: #EBF5FB !important; }}
        [data-testid="stMain"] {{ background-color: #EBF5FB !important; }}

        /* ── Header xanh Tiki ── */
        header[data-testid="stHeader"] {{
            background-color: #1264A3 !important;
            height: {_HEADER_H} !important;
        }}
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] a,
        header[data-testid="stHeader"] [data-testid="stToolbar"] {{
            display: none !important;
        }}

        /* ── Content padding (không cần chừa chỗ sidebar) ── */
        .block-container {{
            padding-top: calc({_HEADER_H} + 0.5rem) !important;
            padding-bottom: 0.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 100% !important;
        }}
        hr {{ margin: 0.4rem 0 !important; }}

        /* ── Brand label cố định đè lên header (bên trái) ── */
        #tiki-brand {{
            position: fixed; top: 0; left: 0;
            height: {_HEADER_H}; z-index: 9999998;
            display: flex; align-items: center;
            padding-left: 1.5rem;
            pointer-events: none;
            font-size: 1.25rem; font-weight: 800;
            color: #ffffff; letter-spacing: 0.02em;
            text-shadow: 0 1px 4px rgba(0,0,0,0.3);
        }}

        /* ── Tabs: nằm cố định trong header, góc phải ── */
        .stTabs [data-baseweb="tab-list"] {{
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            left: auto !important;
            height: {_HEADER_H} !important;
            z-index: 9999999 !important;
            background: transparent !important;
            border-radius: 0 !important;
            padding: 0 0.75rem 0 0 !important;
            gap: 0 !important;
            display: flex !important;
            align-items: center !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: {_HEADER_H} !important;
            background: transparent !important;
            border-radius: 0 !important;
            color: rgba(255,255,255,0.82) !important;
            padding: 0 15px !important;
            font-size: 0.87rem !important;
            font-weight: 500 !important;
            border: none !important;
            border-bottom: 3px solid transparent !important;
            transition: background 0.15s, color 0.15s !important;
            white-space: nowrap !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background: rgba(255,255,255,0.15) !important;
            color: #fff !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: rgba(255,255,255,0.12) !important;
            color: #fff !important;
            font-weight: 700 !important;
            border-bottom: 3px solid #fff !important;
        }}
        .stTabs [data-baseweb="tab-border"],
        .stTabs [data-baseweb="tab-highlight"] {{
            display: none !important;
        }}
        /* Collapse vùng chiếm chỗ của tab-list (đã được fixed) */
        .stTabs > div:first-child {{
            height: 0 !important;
            min-height: 0 !important;
            overflow: visible !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        /* Nền vùng nội dung tab */
        .stTabs [data-baseweb="tab-panel"] {{
            background-color: #EBF5FB !important;
            border: 1px solid #D6EAF8 !important;
            border-radius: 8px !important;
            padding: 1rem 0.5rem 0.5rem !important;
        }}

        /* ── Toggle mù màu (góc trên phải, dưới header) ── */
        .cb-row {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            margin-bottom: 0.35rem;
        }}

        /* ── Filter bar ── */
        .filter-bar {{
            background: #fff;
            border-radius: 10px;
            border: 1px solid #D6EAF8;
            padding: 0.75rem 1rem 0.5rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 1px 5px rgba(18,100,163,0.08);
        }}

        /* ── Typography ── */
        h1 {{ font-size: 1.4rem !important; margin-bottom: 0 !important; }}
        h2 {{ font-size: 1.05rem !important; margin-bottom: 0.15rem !important; }}
        h3 {{ font-size: 0.95rem !important; }}
        p, li, .stMarkdown {{ font-size: 0.85rem !important; }}
        [data-testid="stCaptionContainer"] p {{ font-size: 0.78rem !important; }}

        /* ── Widgets ── */
        [data-testid="stSelectbox"] label,
        [data-testid="stSlider"] label,
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {{ font-size: 0.82rem !important; }}
        [data-testid="stSlider"] {{ margin-bottom: 0.2rem !important; }}
        </style>

        <div id="tiki-brand">📚 Nhà sách Tiki — Dashboard</div>
        """,
        unsafe_allow_html=True,
    )

    df = load_data()

    # ── Toggle mù màu: góc trên phải, dưới header ────────────────────────────
    _, col_cb = st.columns([7, 1])
    with col_cb:
        cb_mode = st.toggle("👁️ Mù màu", key="cb_toggle")

    colors = CB_COLORS if cb_mode else NORMAL_COLORS

    # ── Filter Drill-down ─────────────────────────────────────────────────────
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
    dff = render_drill_down_filter(df)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Tabs (tab-list sẽ được CSS cố định lên header góc phải) ──────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tổng quan",
        "📈 Giá & Discount",
        "🔍 Phân tích 3",
        "📉 Phân tích 4",
    ])

    with tab1:
        render_overview_tab(dff, colors=colors)

    with tab2:
        render_price_tab(dff, colors=colors)

    with tab3:
        st.info("Tab **Phân tích 3** đang được phát triển...")

    with tab4:
        st.info("Tab **Phân tích 4** đang được phát triển...")


if __name__ == "__main__":
    main()
