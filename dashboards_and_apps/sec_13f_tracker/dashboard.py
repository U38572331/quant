import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import importlib
import sys

# Import the tracker logic to allow refreshing data
# Note: Since sec_tracker.py is in the same folder, this works.
import sec_tracker

# --- Page Config ---
st.set_page_config(
    page_title="13F Institutional Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helpers ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('latest_13f_holdings.csv')
        # Clean numeric columns
        df['Value (x$1000)'] = pd.to_numeric(df['Value (x$1000)'], errors='coerce').fillna(0)
        return df
    except FileNotFoundError:
        return pd.DataFrame()

def refresh_data():
    with st.spinner('Fetching latest data from SEC API... This may take a minute.'):
        # Capture current stdout to show progress if possible, but for now just run it.
        # We need to reload the module or just call main. 
        # But main() prints to stdout.
        try:
            sec_tracker.main()
            st.cache_data.clear()
            st.success('Data refreshed successfully!')
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error refreshing data: {e}")

# --- Sidebar ---
st.sidebar.title("13F Tracker")
page = st.sidebar.radio("Navigation", ["🔥 Market Overview (All Assets)", "🏦 Fund Analysis", "ℹ️ Data Info"])

if st.sidebar.button("🔄 Refresh Data form SEC"):
    refresh_data()

# Load Data
df = load_data()

if df.empty:
    st.warning("No data found. Please click 'Refresh Data' to fetch filings.")
    st.stop()

# --- Page: Market Overview ---
if page == "🔥 Market Overview (All Assets)":
    st.title("🔥 Market Overview: The Hot List")
    st.write("Aggregated view of ALL assets held by the tracked funds. Who is betting big on what?")
    
    # Aggregation
    # Group by Issuer (Name) and maybe Class to differentiate Shares/calls/puts if needed.
    # We will simple aggregate by Name for the big picture.
    
    gb = df.groupby(['Issuer', 'CUSIP'])
    
    agg_df = gb.agg({
        'Value (x$1000)': 'sum',
        'Fund': 'nunique', # Count distinct funds holding this
        'Shares': lambda x: pd.to_numeric(x, errors='coerce').sum()
    }).reset_index()
    
    agg_df.rename(columns={'Fund': 'Fund Count', 'Value (x$1000)': 'Total Value ($K)'}, inplace=True)
    
    # Sort
    agg_df = agg_df.sort_values('Total Value ($K)', ascending=False).reset_index(drop=True)
    
    # Top 20 Stats
    top_n = 50
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Top {top_n} Holdings by Conviction (Total Value)")
        fig = px.bar(
            agg_df.head(top_n), 
            x='Total Value ($K)', 
            y='Issuer', 
            orientation='h',
            text='Fund Count',
            hover_data=['CUSIP', 'Total Value ($K)'],
            color='Total Value ($K)',
            color_continuous_scale='Bluered'
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=800)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Key Metrics")
        total_aum = agg_df['Total Value ($K)'].sum()
        st.metric("Total Tracked Assets", f"${total_aum/1000000:,.2f} T")
        st.metric("Unique Securities", f"{len(agg_df):,}")
        
        st.markdown("### Most Popular (by Holder Count)")
        pop_df = agg_df.sort_values('Fund Count', ascending=False).head(10)
        st.table(pop_df[['Issuer', 'Fund Count']])

    st.divider()
    
    # Full Table
    st.subheader("📋 Full Asset List")
    st.dataframe(
        agg_df.style.format({'Total Value ($K)': '${:,.0f}', 'Shares': '{:,.0f}'}),
        use_container_width=True,
        height=600
    )


# --- Page: Fund Analysis ---
elif page == "🏦 Fund Analysis":
    st.title("🏦 Individual Fund Deep Dive")
    
    funds = sorted(df['Fund'].unique())
    selected_fund = st.sidebar.selectbox("Select Fund", funds)
    
    fund_df = df[df['Fund'] == selected_fund].copy()
    
    # Metrics
    fund_value = fund_df['Value (x$1000)'].sum()
    filing_date = fund_df['FilingDate'].iloc[0]
    holdings_count = len(fund_df)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Reported Value", f"${fund_value/1000000:,.2f} B")
    m2.metric("Positions", holdings_count)
    m3.metric("Filing Date", filing_date)
    
    # Visualization
    # Top 10 holdings of this fund
    fund_df_sorted = fund_df.sort_values('Value (x$1000)', ascending=False).head(20)
    
    fig = px.pie(
        fund_df_sorted, 
        values='Value (x$1000)', 
        names='Issuer',
        title=f"Top 20 Positions Concentration ({selected_fund})",
        hole=0.4
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Table
    st.subheader("Positions List")
    st.dataframe(
        fund_df.sort_values('Value (x$1000)', ascending=False).style.format({'Value (x$1000)': '${:,.0f}'}), 
        use_container_width=True,
        height=600
    )

# --- Page: Info ---
elif page == "ℹ️ Data Info":
    st.title("ℹ️ About This Data")
    st.markdown("""
    ### Data Source
    *   **Source**: SEC EDGAR API (13F-HR Filings)
    *   **Updates**: Quarterly (45 days after quarter end)
    *   **Note**: Value is reported in thousands (x$1000).
    """)
    
    st.subheader("Tracked Funds Status")
    
    # Show status table
    status_df = df.groupby(['Fund', 'FilingDate']).size().reset_index(name='Positions')
    st.table(status_df.sort_values('FilingDate'))

