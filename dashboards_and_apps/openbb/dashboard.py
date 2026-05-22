
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from openbb_core.app.provider_interface import ProviderInterface

# Initialize OpenBB (similar to CLI patch)
try:
    import openbb_core.app.provider_interface as pi_module
    pi = ProviderInterface()
    # No need to manually inject here as Streamlit runs in normal python environment,
    # but good to have if we package it later.
except Exception as e:
    st.error(f"Failed to initialize OpenBB Provider Interface: {e}")

from openbb import obb

st.set_page_config(layout="wide", page_title="OpenBB Dashboard")

st.title("OpenBB Local Dashboard")

# Sidebar
category = st.sidebar.selectbox("Category", ["Equity", "Economy", "Crypto"])

if category == "Equity":
    symbol = st.sidebar.text_input("Symbol", "AAPL")
    provider = st.sidebar.selectbox("Provider", ["yfinance", "fmp", "intrinio", "tmx"], index=0)
    
    st.header(f"Equity Data: {symbol}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Get Historical Price"):
            try:
                # OpenBB v4 syntax
                df = obb.equity.price.historical(symbol=symbol, provider=provider).to_df()
                st.dataframe(df.tail(10))
                
                # Chart
                fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'])])
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error fetching data: {e}")

    with col2:
         if st.button("Get Company Info"):
            try:
                # Attempt to get company info if available in standard free providers
                # Note: 'equity.profile' might need specific providers
                info = obb.equity.profile(symbol=symbol, provider=provider) 
                st.write(info)
            except Exception as e:
                st.warning(f"Could not fetch profile (Provider {provider} might not support it): {e}")

elif category == "Economy":
    st.header("Economic Data")
    indicator = st.selectbox("Indicator", ["CPI", "GDP", "Unemployment"])
    
    if st.button("Fetch Data"):
        # Placeholder for economy calls - need to check exact v4 syntax
        st.info(f"Fetching {indicator}...")
        try:
             # Example: CPI
             if indicator == "CPI":
                 data = obb.economy.cpi(provider="fred").to_df()
                 st.line_chart(data)
        except Exception as e:
            st.error(f"Error: {e}")

elif category == "Crypto":
    symbol = st.sidebar.text_input("Symbol", "BTC-USD")
    st.header(f"Crypto Data: {symbol}")
    if st.button("Get Price"):
         try:
             df = obb.crypto.price.historical(symbol=symbol, provider="yfinance").to_df()
             st.line_chart(df['close'])
         except Exception as e:
             st.error(f"Error: {e}")

