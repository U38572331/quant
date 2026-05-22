import pandas as pd
import numpy as np

class ORBRelativeVolumeStrategy:
    """
    Implementation of the 5-Minute ORB Strategy based on "Stocks in Play"
    with Relative Volume tracking.
    """
    def __init__(self, initial_aum=25000.0, commission_per_share=0.0035, max_leverage=4.0):
        self.initial_aum = initial_aum
        self.current_aum = initial_aum
        self.commission = commission_per_share
        self.max_leverage = max_leverage
        
    def calculate_daily_indicators(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the required 14-day daily indicators.
        Must contain columns: High, Low, Close, Volume.
        """
        df = df_daily.copy()
        
        # 1. 14-day Average Volume
        df['AvgVol_14d'] = df['Volume'].rolling(window=14, min_periods=1).mean().shift(1)
        
        # 2. 14-day ATR (Average True Range)
        df['PrevClose'] = df['Close'].shift(1)
        df['TR'] = df[['High', 'Low', 'PrevClose']].apply(
            lambda x: max(
                x['High'] - x['Low'],
                abs(x['High'] - x['PrevClose']) if not pd.isna(x['PrevClose']) else 0,
                abs(x['Low'] - x['PrevClose']) if not pd.isna(x['PrevClose']) else 0
            ), axis=1
        )
        df['ATR_14d'] = df['TR'].rolling(window=14, min_periods=1).mean().shift(1)
        
        return df

    def calculate_first_5min_volume(self, df_intraday: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the Relative Volume of the first 5 minutes (9:30 - 9:35 AM ET).
        df_intraday must be indexed by datetime.
        """
        df = df_intraday.copy()
        
        # Filter for the 9:30 AM - 9:35 AM bar
        # Assuming index is tz-aware or local ET, and bars are 5m labeled at end/start.
        orb_bars = df.between_time('09:30', '09:35')
        
        # Group by date to get daily ORB volume
        orb_bars['Date'] = orb_bars.index.date
        daily_orb_vol = orb_bars.groupby('Date')['Volume'].sum().reset_index()
        daily_orb_vol.set_index('Date', inplace=True)
        daily_orb_vol.rename(columns={'Volume': 'ORVolume'}, inplace=True)
        
        # Calculate 14-day average of the ORVolume
        daily_orb_vol['ORVolume_Avg_14d'] = daily_orb_vol['ORVolume'].rolling(window=14, min_periods=1).mean().shift(1)
        
        # Relative Volume = ORVolume / ORVolume_Avg_14d
        daily_orb_vol['RelativeVolume'] = daily_orb_vol['ORVolume'] / daily_orb_vol['ORVolume_Avg_14d']
        
        return daily_orb_vol

    def select_top_candidates(self, current_date, daily_data_dict: dict, intraday_data_dict: dict) -> list:
        """
        Selects the top 20 stocks to trade today based on the strategy constraints.
        Returns a list of ticker dictionaries.
        """
        candidates = []
        
        for ticker in daily_data_dict.keys():
            df_daily_ticker = daily_data_dict[ticker]
            df_intra_ticker = intraday_data_dict[ticker]
            
            if current_date not in df_daily_ticker.index or current_date not in df_intra_ticker.index:
                continue
                
            # Get today's daily open, and yesterday's indicators
            daily_row = df_daily_ticker.loc[current_date]
            intra_row = df_intra_ticker.loc[current_date]
            
            open_price = daily_row['Open']
            avg_vol_14d = daily_row['AvgVol_14d']
            atr_14d = daily_row['ATR_14d']
            relative_vol = intra_row['RelativeVolume']
            
            # --- Apply Strategy Contraints from Section 4 ---
            
            # 1. Opening price > $5
            if open_price <= 5.0: continue
            
            # 2. Avg trading volume past 14 days >= 1,000,000 shares
            if pd.isna(avg_vol_14d) or avg_vol_14d < 1000000: continue
            
            # 3. ATR past 14 days > $0.50
            if pd.isna(atr_14d) or atr_14d <= 0.50: continue
            
            # 4. Relative Volume >= 100% (1.0)
            if pd.isna(relative_vol) or relative_vol < 1.0: continue
            
            candidates.append({
                'ticker': ticker,
                'rel_vol': relative_vol,
                'atr': atr_14d,
                'open': open_price
            })
            
        # 5. Trade the stocks with the top 20 Relative Volume
        candidates.sort(key=lambda x: x['rel_vol'], reverse=True)
        top_20 = candidates[:20]
        
        return top_20

    def calculate_position_size(self, price, atr):
        """
        Risk management calculations:
        - Stop loss at 10% of ATR.
        - The loss on capital allocated to the position should not exceed 1% total capital (common risk rule).
        - Max leverage constraint: 4x
        """
        stop_loss_distance = 0.10 * atr
        max_loss_amount = self.current_aum * 0.01  # 1% risk rule
        
        shares = max_loss_amount / stop_loss_distance if stop_loss_distance > 0 else 0
        shares = np.floor(shares)
        
        # Enforce max leverage constraint globally (if buying multiple stocks, 
        # position value needs to be tracked across all open positions)
        return shares, stop_loss_distance

# Example Usage:
# if __name__ == "__main__":
#     strategy = ORBRelativeVolumeStrategy()
#     print("Strategy class loaded and ready for backtesting.")
