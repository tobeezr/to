import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CUSTOM CSS
# =========================
st.markdown("""
<style>
.main { background-color: #f8f9fa; }
h1 { color: #667eea; }
h2 { color: #3498db; }
</style>
""", unsafe_allow_html=True)

# =========================
# DATA LOADERS
# =========================
@st.cache_data
def load_excel(path):
    try:
        df = pd.read_excel(path)
        df.columns = (
            df.columns.str.strip()
            .str.upper()
            .str.replace(" ", "_")
        )
        return df
    except Exception as e:
        st.error(f"Error loading {path}: {e}")
        return pd.DataFrame()

@st.cache_data
def prepare_sales_data(df):
    date_cols = ["ORDER_DATE", "DATE", "CREATION_DATE"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df["ORDER_DATE"] = df[col]
            break

    numeric_cols = ["TOTAL_VALUES", "TOTAL_COMMISSION", "TOTAL_ITEM"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "ORDER_DATE" in df.columns:
        df["YEAR_MONTH"] = df["ORDER_DATE"].dt.to_period("M").astype(str)

    return df

@st.cache_data
def prepare_sku_data(df):
    mapping = {
        "ORDER_LINES/PRODUCT/REFERENCE": "SKU",
        "ORDER_LINES/PRODUCT/NAME": "PRODUCT_NAME",
        "ORDER_LINES/QUANTITY": "QUANTITY",
        "ORDER_LINES/UNIT_PRICE": "UNIT_PRICE",
        "ORDER_LINES/TOTAL": "LINE_TOTAL",
        "CREATION_DATE": "ORDER_DATE",
    }

    for old, new in mapping.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    for col in ["QUANTITY", "UNIT_PRICE", "LINE_TOTAL"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "LINE_TOTAL" in df.columns and df["LINE_TOTAL"].sum() == 0:
        if "QUANTITY" in df.columns and "UNIT_PRICE" in df.columns:
            df["LINE_TOTAL"] = df["QUANTITY"] * df["UNIT_PRICE"]

    return df

# =========================
# METRICS
# =========================
def calculate_metrics(df):
    return {
        "revenue": df["TOTAL_VALUES"].sum() if "TOTAL_VALUES" in df.columns else 0,
        "orders": len(df),
        "customers": df["CUSTOMER_ID"].nunique() if "CUSTOMER_ID" in df.columns else 0,
        "avg_order": df["TOTAL_VALUES"].mean() if "TOTAL_VALUES" in df.columns else 0,
    }

# =========================
# MAIN APP
# =========================
def main():
    st.title("📊 Sales Analytics Dashboard")
    st.markdown("### Complete Sales Intelligence System")

    # Load data from repo
    df = load_excel("Sales_Analysis_Results.xlsx")
    df_sku = load_excel("Client_Status_Analysis.xlsx")

    if df.empty:
        st.warning("No sales data found")
        return

    df = prepare_sales_data(df)
    df_sku = prepare_sku_data(df_sku)

    st.success(f"✅ Loaded {len(df):,} sales records")

    # =========================
    # SIDEBAR FILTERS
    # =========================
    st.sidebar.header("🔍 Filters")

    if "ORDER_DATE" in df.columns:
        min_d = df["ORDER_DATE"].min().date()
        max_d = df["ORDER_DATE"].max().date()

        date_range = st.sidebar.date_input(
            "Date range", (min_d, max_d), min_d, max_d
        )

        df = df[
            (df["ORDER_DATE"].dt.date >= date_range[0]) &
            (df["ORDER_DATE"].dt.date <= date_range[1])
        ]

    # =========================
    # TABS
    # =========================
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Overview", "👔 Sales Reps", "⭐ Customers", "📦 Products", "📈 Trends"]
    )

    # =========================
    # TAB 1 – OVERVIEW
    # =========================
    with tab1:
        metrics = calculate_metrics(df)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Revenue", f"${metrics['revenue']:,.0f}")
        c2.metric("📦 Orders", f"{metrics['orders']:,}")
        c3.metric("👥 Customers", f"{metrics['customers']:,}")
        c4.metric("📊 Avg Order", f"${metrics['avg_order']:,.0f}")

        if "STATUS" in df.columns:
            status = df["STATUS"].value_counts().reset_index()
            status.columns = ["Status", "Count"]
            fig = px.pie(status, values="Count", names="Status")
            st.plotly_chart(fig, use_container_width=True)

    # =========================
    # TAB 4 – PRODUCTS
    # =========================
    with tab4:
        if not df_sku.empty and "SKU" in df_sku.columns:
            st.metric("💰 Revenue", f"${df_sku['LINE_TOTAL'].sum():,.0f}")
            st.metric("📦 Units", f"{df_sku['QUANTITY'].sum():,.0f}")
            st.metric("🏷️ SKUs", df_sku["SKU"].nunique())

            top = (
                df_sku.groupby("SKU")["LINE_TOTAL"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )

            fig = px.bar(top, x="SKU", y="LINE_TOTAL")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No SKU data available")

    # =========================
    # TAB 5 – TRENDS
    # =========================
    with tab5:
        if "YEAR_MONTH" in df.columns:
            trend = df.groupby("YEAR_MONTH")["TOTAL_VALUES"].sum().reset_index()
            fig = px.line(trend, x="YEAR_MONTH", y="TOTAL_VALUES", markers=True)
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
