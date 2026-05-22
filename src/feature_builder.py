
import pandas as pd
import numpy as np

class FeatureBuilder:
    def __init__(self, full_df):
        """
        full_df: 1-minute dataframe with continuous contract data.
        """
        self.df = full_df.copy()
        self.daily_df = None
        self.orb_df = None

    def compute_daily_indicators(self):
        """
        Resamples to Daily to compute ATR and Daily Trends.
        Then shifts them by 1 day to align with 'Today'.
        """
        # Resample to Daily
        # Note: A trading day (RTH) is usually 9:30 - 16:15.
        # But futures trade almost 24h. We should use the "Session" definition.
        # A simple way for NQ is to just group by Date.
        # However, Sunday open is Monday data.
        # Let's keep it simple: strict Calendar Date resample.
        
        self.daily_df = self.df.groupby(self.df.index.date).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        })
        self.daily_df.index.name = 'Date'
        self.daily_df.index = pd.to_datetime(self.daily_df.index)
        
        # Calculate ATR(14)
        high = self.daily_df['High']
        low = self.daily_df['Low']
        close = self.daily_df['Close']
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        self.daily_df['ATR_14'] = tr.rolling(window=14).mean()
        self.daily_df['Daily_Vol_SMA_20'] = self.daily_df['Volume'].rolling(window=20).mean()
        
        # We need these features for "Today", so we must shift them forward by 1
        # Because when we trade today, we only know *Yesterday's* ATR.
        self.prev_daily_features = self.daily_df[['Close', 'ATR_14', 'Daily_Vol_SMA_20']].shift(1).rename(columns={
            'Close': 'Prev_Close',
            'ATR_14': 'Prev_ATR',
            'Daily_Vol_SMA_20': 'Prev_Vol_SMA'
        })

    def build_orb_features(self, orb_df):
        """
        Merges ORB stats with Daily indicators and calculates derived features.
        """
        # Ensure orb_df index is datetime
        if not isinstance(orb_df.index, pd.DatetimeIndex):
            orb_df.index = pd.to_datetime(orb_df.index)
            
        # Merge with previous day features
        # Left join on Date
        data = orb_df.join(self.prev_daily_features, on='Date')
        
        # Drop rows with NaN (first 14 days)
        data = data.dropna()
        
        # --- Feature Engineering ---
        
        # 1. Normalized ORB Range
        data['ORB_Range'] = data['ORB_High'] - data['ORB_Low']
        data['Norm_ORB_Range'] = data['ORB_Range'] / data['Prev_ATR']
        
        # 2. Normalized Gap
        # Gap = ORB_Open - Prev_Close
        data['Gap'] = data['ORB_Open'] - data['Prev_Close']
        data['Norm_Gap'] = data['Gap'] / data['Prev_ATR']
        
        # 3. Relative Volume (RVol)
        # We need the average volume of the *ORB period* specifically, not just daily.
        # But we only passed Daily Vol to this func.
        # Let's approximate RVol using (ORB_Volume / Prev_Daily_Vol_SMA) * constant factor?
        # Better: Calculate rolling mean of ORB_Volume itself.
        data['ORB_Vol_SMA_20'] = data['ORB_Volume'].rolling(window=20).mean().shift(1) # Shift 1 to use past mean
        data['RVol'] = data['ORB_Volume'] / data['ORB_Vol_SMA_20']
        
        # 4. ORB Direction / Type
        # Close vs Open
        data['ORB_Body'] = data['ORB_Close'] - data['ORB_Open']
        data['Bullish_ORB'] = (data['ORB_Body'] > 0).astype(int)
        
        # 5. Pattern Features
        # Wick size
        # Upper wick = High - max(Open, Close)
        data['Upper_Wick'] = data['ORB_High'] - data[['ORB_Open', 'ORB_Close']].max(axis=1)
        data['Lower_Wick'] = data[['ORB_Open', 'ORB_Close']].min(axis=1) - data['ORB_Low']
        
        data['Norm_Upper_Wick'] = data['Upper_Wick'] / data['ORB_Range']
        data['Norm_Lower_Wick'] = data['Lower_Wick'] / data['ORB_Range']
        
        # 6. Time Features
        data['DayOfWeek'] = data.index.dayofweek
        data['Month'] = data.index.month
        
        # 7. VWAP Logic (Approximated for the session)
        # Actually in the ORB period, VWAP is Close approx?
        # Let's skip complex VWAP reconstruction for now and stick to Price Action + Vol + ATR
        # Unless user insists on "VWAP".
        # If we had 1m data inside the builder, we could calc exact VWAP for the ORB.
        # Let's say: Is Close > ORB_VWAP?
        # We can approximate ORB_VWAP as (High+Low+Close)/3 roughly or we can't without 1m.
        # But we have `full_df` in `__init__`. We can compute exact ORB VWAP.
        
        print("Calculating exact ORB VWAP...")
        # Get 9:30-9:45 1m data again
        rth_data = self.df.between_time('09:30', '09:44')
        rth_data['PV'] = rth_data['Close'] * rth_data['Volume']
        
        daily_vwap = rth_data.groupby(rth_data.index.date).apply(
            lambda x: x['PV'].sum() / x['Volume'].sum() if x['Volume'].sum() > 0 else x['Close'].mean()
        )
        daily_vwap.name = 'ORB_VWAP'
        daily_vwap.index = pd.to_datetime(daily_vwap.index)
        
        data = data.join(daily_vwap, on='Date')

        # Post-ORB Session Extremes (09:45 - 16:00) for Label Generation
        print("Calculating Session Extremes (09:45 - 16:00)...")
        session_data = self.df.between_time('09:45', '16:00')
        session_extremes = session_data.groupby(session_data.index.date).agg({
            'High': 'max',
            'Low': 'min'
        }).rename(columns={'High': 'Session_High', 'Low': 'Session_Low'})
        session_extremes.index = pd.to_datetime(session_extremes.index)
        data = data.join(session_extremes, on='Date')
        
        # VWAP Deviation
        data['VWAP_Dev'] = (data['ORB_Close'] - data['ORB_VWAP']) / data['Prev_ATR']
        
        data = data.dropna()
        return data

if __name__ == "__main__":
    from data_loader import DataLoader
    
    # Load
    # Load
    path = "ny_orb_analysis/glbx-mdp3-20100606-20191231.ohlcv-1m.csv"
    loader = DataLoader(path)
    loader.load_data()
    df = loader.preprocess()
    orb_stats = loader.get_15m_orb_data()
    
    # Build Features
    fb = FeatureBuilder(df)
    fb.compute_daily_indicators()
    features = fb.build_orb_features(orb_stats)
    
    print(features.head())
    print(features.columns)
    features.to_csv("src/features_debug.csv")
