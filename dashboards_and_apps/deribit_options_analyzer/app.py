import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
from src.client import DeribitClient
from src.calculator import AdvancedCalculator
from src.utils import enrich_data
from src.analytics import MarketAnalyzer

st.set_page_config(page_title="Deribit Quant Terminal", layout="wide", page_icon="💎")

# --- Premium CSS (Glassmorphism & Gradients) ---
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background: radial-gradient(circle at top left, #1a1c24, #0e1117);
        color: #e0e0e0;
    }
    
    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background: rgba(30, 33, 39, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    div[data-testid="stMetricValue"] {
        font-family: 'SF Pro Display', sans-serif;
        font-weight: 600;
        font-size: 28px;
        background: linear-gradient(90deg, #ffffff, #b0b0b0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8b949e;
    }

    /* AI Insight Box */
    .ai-box {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.9), rgba(13, 17, 23, 0.9));
        border: 1px solid rgba(56, 139, 253, 0.3);
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 0 20px rgba(56, 139, 253, 0.1);
        position: relative;
        overflow: hidden;
    }
    .ai-box::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #58a6ff, #8b949e);
    }
    .ai-header {
        color: #58a6ff;
        font-family: 'SF Pro Display', sans-serif;
        font-weight: 700;
        font-size: 20px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: rgba(30, 33, 39, 0.5);
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.05);
        color: #8b949e;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(56, 139, 253, 0.15);
        border: 1px solid rgba(56, 139, 253, 0.4);
        color: #58a6ff;
    }
    
    /* Headers */
    h1 {
        font-family: 'SF Pro Display', sans-serif;
        font-weight: 800;
        background: linear-gradient(90deg, #58a6ff, #a371f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }
    h3 {
        color: #c9d1d9;
        font-weight: 600;
        /* border-left: 4px solid #58a6ff; Removed blue bar */
        padding-left: 0px;
    }
    
    /* DataFrame */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
currency = st.sidebar.radio("Asset", ["BTC", "ETH"], horizontal=True)
st.sidebar.markdown("---")

# --- Main ---
st.title(f"Option Data: {currency}")

@st.cache_data(ttl=10) # Faster refresh for Spot
def load_data(curr):
    client = DeribitClient()
    instruments = client.get_instruments(curr)
    summary = client.get_book_summary_by_currency(curr)
    
    # Force Fetch Spot Index Price
    index_name = f"{curr.lower()}_usd"
    real_spot = client.get_index_price(index_name)
    
    if instruments.empty or summary.empty:
        return pd.DataFrame(), 0
        
    df = enrich_data(instruments, summary, real_spot)
    calc = AdvancedCalculator()
    df = calc.process_dataframe(df)
    return df, real_spot

with st.spinner('Syncing with Exchange...'):
    df, real_spot_price = load_data(currency)

if df.empty:
    st.error("Connection Failed. Retrying...")
else:
    # Data Cleaning
    analyzer = MarketAnalyzer(df)
    analyzer.clean_data()
    # Explicitly set current_price to the Real Spot we fetched
    analyzer.current_price = real_spot_price if real_spot_price and real_spot_price > 0 else df['underlying_price'].iloc[0]
    current_price = analyzer.current_price # For UI
    
    # 1. STRUCTURAL ANALYSIS (Dominant Expiry)
    struct_exp = analyzer.get_dominant_structural_expiry()
    if struct_exp:
        analyzer_struct = MarketAnalyzer(df[df['expiry_date'] == struct_exp])
        struct_label = f"STRUCTURAL ({struct_exp.strftime('%d%b').upper()})"
        
        # Calculate Profile
        # use calculate_gex_profile which wraps dealer logic and adds 'net_gex' alias for compatibility
        gex_struct_df = analyzer_struct.calculate_gex_profile()
        flip_struct = analyzer_struct.find_flip_level(gex_struct_df)
        pain_struct = analyzer_struct.calculate_max_pain()
        summary_struct = analyzer_struct.generate_ai_summary(gex_struct_df, flip_struct, pain_struct, context=struct_label)
    else:
        st.warning("No Structural Expiry (50-140d) found.")
        struct_label = "N/A"
        summary_struct = "No data."
        flip_struct = 0
        pain_struct = 0
        gex_struct_df = pd.DataFrame()

    # 2. LAYERS (Short / Mid)
    # Short-Term (0-7D)
    analyzer_short = analyzer.filter_by_expiry(hours=24*7, mode='under')
    gex_short = analyzer_short.calculate_gex_profile()
    flip_short = analyzer_short.find_flip_level(gex_short)
    pain_short = analyzer_short.calculate_max_pain()
    summary_short = analyzer_short.generate_ai_summary(gex_short, flip_short, pain_short, context="SHORT-TERM (0-7D)")

    # Mid-Term (14-45D) -> Using filter logic, or specific month?
    # User said "Mid-term: 14-45D".
    # Implementation: Filter explicit logic.
    mid_df = analyzer.df[analyzer.df['hours_to_expiry'].between(14*24, 45*24)]
    analyzer_mid = MarketAnalyzer(mid_df)
    gex_mid = analyzer_mid.calculate_gex_profile()
    flip_mid = analyzer_mid.find_flip_level(gex_mid)
    pain_mid = analyzer_mid.calculate_max_pain()
    summary_mid = analyzer_mid.generate_ai_summary(gex_mid, flip_mid, pain_mid, context="MID-TERM (14-45D)")

    # 3. QUARTERS (Standard)
    # Just list them or pick next major? User: "同時計算最近的 3 / 6 / 9 / 12 月標準季度"
    quarters = analyzer.get_standard_quarters()
    # Let's pick the first one as "Next Quarter"
    if quarters:
        q1 = quarters[0]
        analyzer_q1 = MarketAnalyzer(df[df['expiry_date'] == q1])
        q1_label = f"QTR ({q1.strftime('%d%b').upper()})"
        gex_q1 = analyzer_q1.calculate_gex_profile()
        flip_q1 = analyzer_q1.find_flip_level(gex_q1)
        pain_q1 = analyzer_q1.calculate_max_pain()
        summary_q1 = analyzer_q1.generate_ai_summary(gex_q1, flip_q1, pain_q1, context=q1_label)
    else:
        summary_q1 = "No standard quarter found."
        q1_label = "QTR"
        flip_q1 = 0

    # --- Metrics ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spot Price", f"${current_price:,.2f}")
    c2.metric("Struct Flip", f"${flip_struct:,.0f}", delta=f"{current_price-flip_struct:.0f}", delta_color="inverse")
    c3.metric("Short Flip", f"${flip_short:,.0f}", delta=f"{current_price-flip_short:.0f}", delta_color="inverse")
    c4.metric(f"Max Pain ({struct_label})", f"${pain_struct:,.0f}")

    # --- AI Insight ---
    st.markdown(f"""
<div class="ai-box">
<div class="ai-header">QUANT STRUCTURE</div>
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px;">
    <div>{summary_short}</div>
    <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">{summary_mid}</div>
    <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">{summary_struct}</div>
    <div style="border-left: 1px solid rgba(255,255,255,0.1); padding-left: 20px;">{summary_q1}</div>
</div>
</div>
""", unsafe_allow_html=True)

    # --- Gamma Density Curve (Structural) ---
    st.markdown(f"### GAMMA STRUCTURE: {struct_label}")
    
    col_gex1, col_gex2 = st.columns([2, 1])
    
    with col_gex1:
        st.caption("Dealer Net Gamma Profile (Short Vol Assumption)")
        if not gex_struct_df.empty:
            lower = current_price * 0.75
            upper = current_price * 1.25
            chart_df = gex_struct_df[(gex_struct_df['strike'] > lower) & (gex_struct_df['strike'] < upper)]
            
            # --- Professional WAVE Chart Logic (Unified) ---
            # Use the same curve generator as the Analytics Engine
            # Note: We need the analyzer instance that corresponds to this chart_df
            # Since we iterate generic chart_df, let's instantiate a temp analyzer or helper.
            # Actually, `get_gex_curve` is stateless mostly, but bound to class.
            # We can use the main analyzer instance if it has the method.
            
            curve = analyzer.get_gex_curve(chart_df, num_points=500)
            
            if curve:
                x_smooth = curve['x']
                y_smooth = curve['y']
            else:
                 # Fallback
                 x_smooth = chart_df['strike']
                 y_smooth = chart_df['net_gex']
            
            # 2. Split into Positive (Green) and Negative (Red)
            y_pos = np.maximum(0, y_smooth)
            y_neg = np.minimum(0, y_smooth)
            
            fig = go.Figure()
            
            # Positive Area (Green)
            fig.add_trace(go.Scatter(
                x=x_smooth, y=y_pos,
                mode='lines',
                name='Positive Gamma',
                line=dict(width=0, color='#00e676'), 
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.2)' 
            ))
            # Negative Area (Red)
            fig.add_trace(go.Scatter(
                x=x_smooth, y=y_neg,
                mode='lines',
                name='Negative Gamma',
                line=dict(width=0, color='#ff1744'),
                fill='tozeroy',
                fillcolor='rgba(255, 23, 68, 0.2)' 
            ))
            
            # Net Line (White Ghost)
            fig.add_trace(go.Scatter(
                 x=x_smooth, y=y_smooth,
                 mode='lines',
                 name='Net GEX',
                 line=dict(width=1, color='rgba(255,255,255,0.5)')
            ))

            # Key Levels
            fig.add_vline(x=pain_struct, line_width=1, line_dash="dash", line_color="#00e676")
            fig.add_annotation(x=pain_struct, y=0, text=f"Max Pain", font=dict(color="#00e676"), ay=-20)
            
            if flip_struct > x_smooth.min() and flip_struct < x_smooth.max():
                 fig.add_vline(x=flip_struct, line_width=1, line_dash="dot", line_color="#ffd700")
                 fig.add_annotation(x=flip_struct, y=0, text=f"Flip", font=dict(color="#ffd700"), ay=20)

            fig.add_vline(x=current_price, line_width=1, line_color="#ffffff")
            fig.add_annotation(x=current_price, y=y_smooth.min(), text="Spot", font=dict(color="#ffffff"), showarrow=False)

            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=400,
                xaxis=dict(showgrid=False, title="Strike Price"),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', title="Dealer Net Gamma ($)"),
                hovermode="x unified",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No structural data available.")

    with col_gex2:
        st.caption("Short-Term (0-7D) Profile")
        # Reuse logic for short term if needed, or simple Bar
        if not gex_short.empty:
             chart_df_s = gex_short[(gex_short['strike'] > lower) & (gex_short['strike'] < upper)]
             fig_s = go.Figure()
             fig_s.add_trace(go.Bar(
                 x=chart_df_s['strike'], y=chart_df_s['net_gex'],
                 marker_color='#ff1744', opacity=0.8
             ))
             fig_s.add_vline(x=current_price, line_color="white")
             fig_s.update_layout(
                 template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                 height=400, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
             )
             st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("---")
    st.markdown("### ADVANCED GREEKS")
    
    col_greek1, col_greek2 = st.columns(2)
    
    with col_greek1:
        st.caption("VANNA (Delta / Vol)")
        heatmap_data = df.pivot_table(index='expiry_date', columns='strike', values='vanna', aggfunc='sum')
        cols = [c for c in heatmap_data.columns if lower < c < upper]
        heatmap_data = heatmap_data[cols]
        heatmap_data.index = heatmap_data.index.strftime('%Y-%m-%d')
        
        fig_vanna = px.imshow(
            heatmap_data, 
            aspect='auto', 
            color_continuous_scale='RdBu_r',
            template="plotly_dark"
        )
        fig_vanna.update_layout(height=350, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_vanna, use_container_width=True)

    with col_greek2:
        st.caption("CHARM (Delta / Time)")
        charm_data = df.pivot_table(index='expiry_date', columns='strike', values='charm', aggfunc='sum')
        charm_data = charm_data[cols]
        charm_data.index = charm_data.index.strftime('%Y-%m-%d')
        
        fig_charm = px.imshow(
            charm_data, 
            aspect='auto', 
            color_continuous_scale='RdBu',
            template="plotly_dark"
        )
        fig_charm.update_layout(height=350, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_charm, use_container_width=True)

    st.markdown("---")
    st.markdown("### ORDER FLOW")
    
    st.dataframe(df.style.format({
        'underlying_price': "{:.2f}",
        'mark_price': "{:.4f}",
        'mark_iv': "{:.1f}%",
        'delta': "{:.3f}",
        'gamma': "{:.4f}",
        'vanna': "{:.4f}",
        'charm': "{:.4f}"
    }), height=400)

# --- Sidebar Footer ---
st.sidebar.markdown("---")
with st.sidebar.expander("Debug Info"):
    st.write(f"Rows Cleaned: {len(df)}")
    st.write(f"Struct Exp: {struct_exp.date() if struct_exp else 'None'}")
    gex_val = gex_struct_df['net_gex'].sum()/1e6 if 'gex_struct_df' in locals() and not gex_struct_df.empty else 0
    st.write(f"GEX Total: ${gex_val:.1f}M")
    
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=False)
refresh_rate = st.sidebar.slider("Interval (s)", 5, 60, 10)

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
