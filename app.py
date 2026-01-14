import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page Config
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1 {color: #667eea;}
    h2 {color: #3498db;}
    </style>
""", unsafe_allow_html=True)

# Helper Functions
@st.cache_data
def load_sales_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    df.columns = df.columns.str.strip().str.upper().str.replace(' ', '_')
    
    date_cols = ['ORDER_DATE', 'DATE', 'CREATION_DATE']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df['ORDER_DATE'] = df[col]
            break
    
    numeric_cols = ['TOTAL_ITEM', 'TOTAL_VALUES', 'TOTAL_COMMISSION']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'ORDER_DATE' in df.columns:
        df['YEAR_MONTH'] = df['ORDER_DATE'].dt.to_period('M').astype(str)
        df['YEAR'] = df['ORDER_DATE'].dt.year
        df['MONTH'] = df['ORDER_DATE'].dt.month
    
    return df

@st.cache_data
def load_sku_data(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    df.columns = df.columns.str.strip().str.upper()
    
    mapping = {
        'MATRIX_ORDER_ID': 'ORDER_ID',
        'CREATION_DATE': 'ORDER_DATE',
        'ORDER_LINES/PRODUCT/REFERENCE': 'SKU',
        'ORDER_LINES/PRODUCT/NAME': 'PRODUCT_NAME',
        'ORDER_LINES/QUANTITY': 'QUANTITY',
        'ORDER_LINES/UNIT_PRICE': 'UNIT_PRICE',
        'ORDER_LINES/TOTAL': 'LINE_TOTAL',
    }
    
    for old, new in mapping.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)
    
    for col in ['QUANTITY', 'UNIT_PRICE', 'LINE_TOTAL']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    if 'LINE_TOTAL' in df.columns and df['LINE_TOTAL'].sum() == 0:
        if 'QUANTITY' in df.columns and 'UNIT_PRICE' in df.columns:
            df['LINE_TOTAL'] = df['QUANTITY'] * df['UNIT_PRICE']
    
    if 'ORDER_DATE' in df.columns:
        df['ORDER_DATE'] = pd.to_datetime(df['ORDER_DATE'], errors='coerce')
        df['YEAR_MONTH'] = df['ORDER_DATE'].dt.to_period('M').astype(str)
    
    return df

def calculate_metrics(df):
    return {
        'total_revenue': df['TOTAL_VALUES'].sum() if 'TOTAL_VALUES' in df.columns else 0,
        'total_orders': len(df),
        'total_commission': df['TOTAL_COMMISSION'].sum() if 'TOTAL_COMMISSION' in df.columns else 0,
        'unique_customers': df['CUSTOMER_ID'].nunique() if 'CUSTOMER_ID' in df.columns else 0,
        'avg_order_value': df['TOTAL_VALUES'].mean() if 'TOTAL_VALUES' in df.columns else 0,
        'unique_reps': df['SALE_REPRESENTATIVE'].nunique() if 'SALE_REPRESENTATIVE' in df.columns else 0
    }

# Main App
def main():
    st.title("📊 Sales Analytics Dashboard")
    st.markdown("### Complete Sales Intelligence System")
    
    # Sidebar
    st.sidebar.header("📁 Data Upload")
    
    sales_file = st.sidebar.file_uploader(
        "Upload Sales Data",
        type=['csv', 'xlsx'],
        help="Main sales/orders file"
    )
    
    sku_file = st.sidebar.file_uploader(
        "Upload SKU/Product Data (Optional)",
        type=['csv', 'xlsx'],
        help="Order lines/SKU file"
    )
    
    if not sales_file:
        st.info("👈 Upload your sales data to begin")
        st.markdown("""
        ### Required Columns:
        - ORDER DATE
        - CUSTOMER ID / NAME
        - SALE REPRESENTATIVE
        - STATUS
        - TOTAL VALUES
        - TOTAL COMMISSION
        """)
        return
    
    # Load data
    with st.spinner("Loading..."):
        df = load_sales_data(sales_file)
        df_sku = load_sku_data(sku_file) if sku_file else None
    
    st.success(f"✅ Loaded {len(df):,} records")
    
    # Filters
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filters")
    
    # Date filter
    if 'ORDER_DATE' in df.columns:
        min_date = df['ORDER_DATE'].min().date()
        max_date = df['ORDER_DATE'].max().date()
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            df = df[(df['ORDER_DATE'].dt.date >= date_range[0]) & 
                   (df['ORDER_DATE'].dt.date <= date_range[1])]
    
    # Sales Rep filter
    if 'SALE_REPRESENTATIVE' in df.columns:
        reps = ['All'] + sorted(df['SALE_REPRESENTATIVE'].dropna().unique().tolist())
        selected_reps = st.sidebar.multiselect("Sales Reps", reps, ['All'])
        if 'All' not in selected_reps:
            df = df[df['SALE_REPRESENTATIVE'].isin(selected_reps)]
    
    # Status filter
    if 'STATUS' in df.columns:
        statuses = ['All'] + sorted(df['STATUS'].dropna().unique().tolist())
        selected_status = st.sidebar.multiselect("Status", statuses, ['All'])
        if 'All' not in selected_status:
            df = df[df['STATUS'].isin(selected_status)]
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "👔 Sales Reps", "⭐ Customers", 
        "📦 Products", "📈 Trends"
    ])
    
    # TAB 1: OVERVIEW
    with tab1:
        st.header("Executive Overview")
        
        metrics = calculate_metrics(df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Revenue", f"${metrics['total_revenue']:,.0f}")
        with col2:
            st.metric("📦 Orders", f"{metrics['total_orders']:,}")
        with col3:
            st.metric("👥 Customers", f"{metrics['unique_customers']:,}")
        with col4:
            st.metric("📊 Avg Order", f"${metrics['avg_order_value']:,.0f}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'STATUS' in df.columns:
                st.subheader("Status Distribution")
                status_data = df['STATUS'].value_counts().reset_index()
                status_data.columns = ['Status', 'Count']
                fig = px.pie(status_data, values='Count', names='Status',
                           color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'SALE_REPRESENTATIVE' in df.columns:
                st.subheader("Top 5 Sales Reps")
                top_reps = df.groupby('SALE_REPRESENTATIVE')['TOTAL_VALUES'].sum().nlargest(5).reset_index()
                fig = go.Figure(go.Bar(
                    x=top_reps['SALE_REPRESENTATIVE'],
                    y=top_reps['TOTAL_VALUES'],
                    marker_color='#3498db'
                ))
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: SALES REPS
    with tab2:
        st.header("Sales Representative Performance")
        
        if 'SALE_REPRESENTATIVE' in df.columns:
            top_n = st.slider("Show Top N", 5, 30, 10)
            
            rep_perf = df.groupby('SALE_REPRESENTATIVE').agg({
                'TOTAL_VALUES': 'sum',
                'ORDER_NUMBER': 'count',
                'CUSTOMER_ID': 'nunique',
                'TOTAL_COMMISSION': 'sum'
            }).sort_values('TOTAL_VALUES', ascending=False).head(top_n).reset_index()
            
            rep_perf.columns = ['Rep', 'Revenue', 'Orders', 'Customers', 'Commission']
            
            fig = go.Figure(go.Bar(
                x=rep_perf['Rep'],
                y=rep_perf['Revenue'],
                marker_color='#3498db',
                text=rep_perf['Revenue'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside'
            ))
            fig.update_layout(title=f'Top {top_n} Reps by Revenue', height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(rep_perf.style.format({
                'Revenue': '${:,.0f}',
                'Orders': '{:,}',
                'Customers': '{:,}',
                'Commission': '${:,.0f}'
            }), use_container_width=True)
    
    # TAB 3: CUSTOMERS
    with tab3:
        st.header("Customer Analysis")
        
        if 'CUSTOMER_ID' in df.columns:
            top_n = st.slider("Show Top N", 5, 30, 10, key='cust')
            
            cust_perf = df.groupby(['CUSTOMER_ID', 'CUSTOMER_NAME']).agg({
                'TOTAL_VALUES': 'sum',
                'ORDER_NUMBER': 'count'
            }).sort_values('TOTAL_VALUES', ascending=False).head(top_n).reset_index()
            
            cust_perf.columns = ['ID', 'Customer', 'Revenue', 'Orders']
            
            fig = go.Figure(go.Bar(
                x=cust_perf['Customer'],
                y=cust_perf['Revenue'],
                marker_color='#e67e22',
                text=cust_perf['Revenue'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside'
            ))
            fig.update_layout(title=f'Top {top_n} Customers', height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(cust_perf.style.format({
                'Revenue': '${:,.0f}',
                'Orders': '{:,}'
            }), use_container_width=True)
    
    # TAB 4: PRODUCTS
    with tab4:
        st.header("Product Analysis")
        
        if df_sku is not None and 'SKU' in df_sku.columns:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Revenue", f"${df_sku['LINE_TOTAL'].sum():,.0f}")
            with col2:
                st.metric("📦 Units", f"{df_sku['QUANTITY'].sum():,.0f}")
            with col3:
                st.metric("🏷️ SKUs", f"{df_sku['SKU'].nunique():,}")
            
            st.markdown("---")
            
            top_n = st.slider("Top N Products", 5, 20, 10, key='sku')
            
            sku_cols = ['SKU']
            if 'PRODUCT_NAME' in df_sku.columns:
                sku_cols.append('PRODUCT_NAME')
            
            sku_perf = df_sku.groupby(sku_cols).agg({
                'QUANTITY': 'sum',
                'LINE_TOTAL': 'sum'
            }).sort_values('LINE_TOTAL', ascending=False).head(top_n).reset_index()
            
            display_col = 'PRODUCT_NAME' if 'PRODUCT_NAME' in sku_perf.columns else 'SKU'
            
            fig = go.Figure(go.Bar(
                x=sku_perf[display_col],
                y=sku_perf['LINE_TOTAL'],
                marker_color='#2ecc71',
                text=sku_perf['LINE_TOTAL'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside'
            ))
            fig.update_layout(title='Top Products by Revenue', height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Upload SKU data to view product analysis")
    
    # TAB 5: TRENDS
    with tab5:
        st.header("Sales Trends")
        
        if 'YEAR_MONTH' in df.columns:
            monthly = df.groupby('YEAR_MONTH').agg({
                'TOTAL_VALUES': 'sum',
                'ORDER_NUMBER': 'count'
            }).reset_index()
            
            monthly.columns = ['Month', 'Revenue', 'Orders']
            
            fig1 = go.Figure(go.Scatter(
                x=monthly['Month'],
                y=monthly['Revenue'],
                mode='lines+markers',
                line=dict(color='#3498db', width=3),
                fill='tozeroy'
            ))
            fig1.update_layout(title='Monthly Revenue', height=400)
            st.plotly_chart(fig1, use_container_width=True)
            
            fig2 = go.Figure(go.Bar(
                x=monthly['Month'],
                y=monthly['Orders'],
                marker_color='#2ecc71'
            ))
            fig2.update_layout(title='Monthly Orders', height=400)
            st.plotly_chart(fig2, use_container_width=True)

if __name__ == "__main__":
    main()
