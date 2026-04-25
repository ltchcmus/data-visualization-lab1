"""Machine Learning tab — model results, feature importance, clustering, prediction."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import joblib

from ..format_utils import apply_chart_style, format_vn
from ..ui_cards import render_kpi_section, render_metric_strip

# ---------------------------------------------------------------------------
# Artifact paths
# ---------------------------------------------------------------------------
_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "notebooks" / "model" / "artifacts"


@st.cache_resource(show_spinner=False)
def _load_artifacts():
    """Load all model artifacts once and cache."""
    rf_model = joblib.load(_ARTIFACTS_DIR / "rf_model.pkl")
    kmeans = joblib.load(_ARTIFACTS_DIR / "kmeans_model.pkl")
    cluster_scaler = joblib.load(_ARTIFACTS_DIR / "cluster_scaler.pkl")
    metadata = joblib.load(_ARTIFACTS_DIR / "ml_metadata.pkl")

    feat_imp_path = _ARTIFACTS_DIR / "feature_importance.csv"
    if feat_imp_path.exists():
        feat_imp = pd.read_csv(feat_imp_path)
    else:
        feat_imp = pd.DataFrame({
            "feature": metadata["features"],
            "importance": rf_model.feature_importances_,
        })

    return rf_model, kmeans, cluster_scaler, metadata, feat_imp


# ---------------------------------------------------------------------------
# ML data loaders
# ---------------------------------------------------------------------------
_PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


@st.cache_data(show_spinner=False)
def _load_ml_data():
    return pd.read_csv(_PROCESSED_DIR / "data_ml.csv")


@st.cache_data(show_spinner=False)
def _load_eda_data():
    return pd.read_csv(_PROCESSED_DIR / "data_eda.csv", low_memory=False)


# ---------------------------------------------------------------------------
# Sub-sections
# ---------------------------------------------------------------------------


def _render_model_kpis(rf_model, metadata, feat_imp) -> None:
    """Quick model stats KPI cards."""
    from sklearn.metrics import root_mean_squared_error, r2_score, mean_absolute_error
    from sklearn.model_selection import train_test_split

    df_ml = _load_ml_data()
    ml_features = metadata["features"]
    X = df_ml[ml_features]
    y = df_ml["log_sales"]
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    y_pred = rf_model.predict(X_test)

    rmse = root_mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    n_features = len(ml_features)
    top_feat = feat_imp.sort_values("importance", ascending=False).iloc[0]["feature"]

    render_kpi_section(
        [
            {
                "label": "R² Score",
                "value": f"{r2:.4f}",
                "icon": "target",
                "tone": "emerald" if r2 > 0.75 else "amber",
                "subtitle": f"Model giải thích {r2*100:.1f}% phương sai.",
            },
            {
                "label": "RMSE",
                "value": f"{rmse:.4f}",
                "icon": "chart",
                "tone": "blue",
                "subtitle": "Root Mean Squared Error trên test set.",
            },
            {
                "label": "MAE",
                "value": f"{mae:.4f}",
                "icon": "chart",
                "tone": "slate",
                "subtitle": f"Lệch thực tế ≈ {np.exp(mae):.2f}x.",
            },
            {
                "label": "Số features",
                "value": str(n_features),
                "icon": "tag",
                "tone": "violet",
                "subtitle": f"Feature #1: {top_feat}.",
            },
            {
                "label": "Model",
                "value": "Random Forest",
                "icon": "building",
                "tone": "blue",
                "subtitle": f"{rf_model.n_estimators} trees, max_depth={rf_model.max_depth}.",
            },
        ],
        title="HIỆU SUẤT MÔ HÌNH DỰ ĐOÁN",
        summary="Random Forest Regressor dự đoán log(doanh_số) dựa trên đặc trưng sản phẩm.",
        footnote=f"Đánh giá trên test set ({X_test.shape[0]} mẫu), train/test split 80/20, random_state=42.",
    )


def _render_feature_importance(feat_imp, colors) -> None:
    """Horizontal bar chart of feature importances."""
    df = feat_imp.sort_values("importance", ascending=True).tail(15).copy()

    # Prettify feature names
    name_map = {
        "price": "Giá sách",
        "discount_rate_norm": "Tỷ lệ giảm giá",
        "rating_average": "Điểm rating TB",
        "number_of_page": "Số trang",
        "log_review_count": "Số lượt review (log)",
        "is_high_rating": "Rating cao (>4.5)",
        "is_heavy_book": "Sách dày (>300 trang)",
    }
    df["display"] = df["feature"].apply(
        lambda f: name_map.get(f, f.replace("publisher_vn_mapped_", "NXB: ").replace("cat_level_2_mapped_", "DM: "))
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["importance"],
            y=df["display"],
            orientation="h",
            marker_color=[
                "#ef4444" if v > 0.1 else "#f59e0b" if v > 0.02 else "#94a3b8"
                for v in df["importance"]
            ],
            text=[f"{v:.1%}" for v in df["importance"]],
            textposition="outside",
            textfont=dict(size=11),
        )
    )
    fig.update_layout(
        title="Top features ảnh hưởng đến doanh số",
        xaxis_title="Mức quan trọng (Importance)",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    apply_chart_style(fig, height=max(300, len(df) * 28))
    st.plotly_chart(fig, use_container_width=True, key="ml_feat_imp")


def _render_actual_vs_predicted(rf_model, metadata) -> None:
    """Scatter plot of actual vs predicted."""
    from sklearn.model_selection import train_test_split

    df_ml = _load_ml_data()
    X = df_ml[metadata["features"]]
    y = df_ml["log_sales"]
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    y_pred = rf_model.predict(X_test)

    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=y_test,
            y=y_pred,
            mode="markers",
            marker=dict(color="#3b82f6", opacity=0.15, size=4),
            name="Predictions",
        )
    )
    lims = [min(y_test.min(), y_pred.min()) - 0.3, max(y_test.max(), y_pred.max()) + 0.3]
    fig.add_trace(
        go.Scatter(
            x=lims,
            y=lims,
            mode="lines",
            line=dict(color="#ef4444", dash="dash", width=2),
            name="Perfect prediction",
        )
    )
    fig.update_layout(
        title="Actual vs Predicted (log sales)",
        xaxis_title="Actual log(sales)",
        yaxis_title="Predicted log(sales)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    apply_chart_style(fig, height=420)
    st.plotly_chart(fig, use_container_width=True, key="ml_actual_pred")


def _render_clusters(kmeans, cluster_scaler, colors) -> None:
    """Market segmentation visualization."""
    df_eda = _load_eda_data()

    cluster_feats = ["rating_average", "price", "review_count"]
    df_eda["log_sales_cl"] = np.log1p(df_eda["all_time_quantity_sold"].fillna(0))
    cluster_cols = ["log_sales_cl"] + cluster_feats
    X_cl = df_eda[cluster_cols].fillna(0)
    df_eda["cluster"] = kmeans.predict(cluster_scaler.transform(X_cl))

    # Profile
    profile = df_eda.groupby("cluster").agg(
        count=("cluster", "size"),
        avg_sales=("all_time_quantity_sold", "mean"),
        avg_rating=("rating_average", "mean"),
        avg_price=("price", "mean"),
        avg_reviews=("review_count", "mean"),
    ).round(1)

    # Name clusters (đảm bảo 4 tên phân biệt dựa trên rank tương đối)
    sales_sorted = profile.sort_values("avg_sales", ascending=False).index.tolist()
    
    cluster_names = {}
    cluster_names[sales_sorted[0]] = "Best Seller"
    cluster_names[sales_sorted[-1]] = "Low Performer"
    
    rem = sales_sorted[1:3]
    if profile.loc[rem[0], "avg_rating"] > profile.loc[rem[1], "avg_rating"]:
        cluster_names[rem[0]] = "Niche"
        cluster_names[rem[1]] = "Normal"
    else:
        cluster_names[rem[1]] = "Niche"
        cluster_names[rem[0]] = "Normal"

    df_eda["cluster_name"] = df_eda["cluster"].map(cluster_names)

    # KPIs strip
    kpi_items = []
    for c in sorted(profile.index):
        r = profile.loc[c]
        name = cluster_names[c]
        tone = ["blue", "amber", "emerald", "violet"][c % 4]
        kpi_items.append({
            "label": f"{name}",
            "value": f"{format_vn(int(r['count']))} sách",
            "icon": "book",
            "tone": tone,
        })
    render_metric_strip(kpi_items, compact=True, cols=4)

    # Scatter: Rating vs Sales by cluster
    sample = df_eda.groupby("cluster", group_keys=False).apply(
        lambda x: x.sample(min(len(x), 1500), random_state=42)
    )
    cluster_colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"]
    color_map = {cluster_names[c]: cluster_colors[c % 4] for c in sorted(profile.index)}

    fig = px.scatter(
        sample,
        x="rating_average",
        y="log_sales_cl",
        color="cluster_name",
        color_discrete_map=color_map,
        opacity=0.35,
        labels={
            "rating_average": "Rating",
            "log_sales_cl": "log(Doanh số)",
            "cluster_name": "Phân khúc",
        },
    )
    fig.update_traces(marker=dict(size=5))
    fig.update_layout(
        title="Phân khúc thị trường sách (KMeans Clustering)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    apply_chart_style(fig, height=420)
    st.plotly_chart(fig, use_container_width=True, key="ml_cluster_scatter")

    # Cluster detail table
    display = profile.copy()
    display["Phân khúc"] = [cluster_names[c] for c in display.index]
    display = display.rename(columns={
        "count": "Số sách",
        "avg_sales": "Doanh số TB",
        "avg_rating": "Rating TB",
        "avg_price": "Giá TB (₫)",
        "avg_reviews": "Reviews TB",
    })
    display = display[["Phân khúc", "Số sách", "Doanh số TB", "Rating TB", "Giá TB (₫)", "Reviews TB"]]
    st.dataframe(display, use_container_width=True, hide_index=True)


def _render_prediction_form(rf_model, metadata) -> None:
    """Interactive prediction form."""
    ml_features = metadata["features"]
    top_pubs = metadata["top_publishers"]
    top_cats = metadata["top_cats"]

    st.markdown(
        "<div style='margin-top:8px; margin-bottom:16px;'>"
        "<span style='font-size:1.1rem; font-weight:700; color:#1e293b;'>Dự đoán doanh số</span>"
        "<span style='font-size:0.82rem; color:#64748b; margin-left:8px;'>"
        "Nhập thông tin sách để model dự đoán lượng bán.</span></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        price = st.number_input("Giá sách (VND)", min_value=0, value=150000, step=10000, key="ml_price")
        rating = st.slider("Rating", 0.0, 5.0, 4.2, 0.1, key="ml_rating")
    with c2:
        discount = st.slider("Chiết khấu (%)", 0, 80, 20, 5, key="ml_discount")
        n_pages = st.number_input("Số trang", min_value=10, value=250, step=10, key="ml_pages")
    with c3:
        reviews = st.number_input("Số lượt review", min_value=0, value=15, step=1, key="ml_reviews")
        publisher = st.selectbox("Nhà xuất bản", ["Other"] + top_pubs, key="ml_pub")
        category = st.selectbox("Danh mục", ["Other"] + top_cats, key="ml_cat")

    if st.button("Dự đoán", key="ml_predict_btn", use_container_width=True):
        # Build feature row
        row = {
            "price": price,
            "discount_rate_norm": discount / 100.0,
            "rating_average": rating,
            "number_of_page": n_pages,
            "log_review_count": np.log1p(reviews),
            "is_high_rating": int(rating > 4.5),
            "is_heavy_book": int(n_pages > 300),
        }

        pub_mapped = publisher if publisher in top_pubs else "Other"
        for p in top_pubs + ["Other"]:
            row[f"publisher_vn_mapped_{p}"] = 1 if p == pub_mapped else 0

        cat_mapped = category if category in top_cats else "Other"
        for c in top_cats + ["Other"]:
            row[f"cat_level_2_mapped_{c}"] = 1 if c == cat_mapped else 0

        df_row = pd.DataFrame([row])
        for col in ml_features:
            if col not in df_row.columns:
                df_row[col] = 0
        df_row = df_row[ml_features]

        log_pred = rf_model.predict(df_row)[0]
        pred_sales = int(np.expm1(log_pred))

        # Display result
        if pred_sales > 1000:
            tone = "emerald"
            verdict = "Best Seller tiềm năng!"
        elif pred_sales > 100:
            tone = "blue"
            verdict = "Doanh số tốt."
        elif pred_sales > 20:
            tone = "amber"
            verdict = "Doanh số trung bình."
        else:
            tone = "red"
            verdict = "Doanh số thấp."

        render_metric_strip(
            [
                {"label": "Doanh số dự đoán", "value": f"{format_vn(pred_sales)} cuốn", "icon": "chart", "tone": tone},
                {"label": "log(sales)", "value": f"{log_pred:.3f}", "icon": "chart", "tone": "slate"},
                {"label": "Nhận định", "value": verdict, "icon": "star", "tone": tone},
            ],
            compact=True,
            cols=3,
        )


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_machine_learning_tab(
    df: pd.DataFrame,
    *,
    colors: list[str],
    heatmap_scale: str,
) -> None:
    """Render the Machine Learning tab."""
    if not _ARTIFACTS_DIR.exists():
        st.warning("Chưa tìm thấy model artifacts. Vui lòng chạy notebook `train.ipynb` trước.")
        return

    try:
        rf_model, kmeans, cluster_scaler, metadata, feat_imp = _load_artifacts()
    except Exception as e:
        st.error(f"Lỗi load artifacts: {e}")
        return

    # 1. Model Performance KPIs
    _render_model_kpis(rf_model, metadata, feat_imp)

    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

    # 2. Feature Importance + Actual vs Predicted (2 columns)
    col1, col2 = st.columns(2)
    with col1:
        _render_feature_importance(feat_imp, colors)
    with col2:
        _render_actual_vs_predicted(rf_model, metadata)

    # 3. Clustering
    st.markdown(
        "<div style='margin-top:20px; margin-bottom:8px;'>"
        "<span style='font-size:1.05rem; font-weight:700; color:#1e293b;'>Phân khúc thị trường (KMeans)</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    _render_clusters(kmeans, cluster_scaler, colors)

    # 4. Prediction form
    _render_prediction_form(rf_model, metadata)

    st.markdown('<div style="margin-top: 50px;"></div>', unsafe_allow_html=True)
