
import pandas as pd
import numpy as np

class LabelGenerator:
    def __init__(self, full_df):
        self.df = full_df
    
    def generate_labels(self, orb_stats):
        """
        Iterates through each day in orb_stats and calculates outcome metrics.
        Returns orb_stats with new columns.
        """
        print("Generating training labels (MFE/MAE)...")
        
        # Prepare columns
        labels = {
            'Long_MFE': [], 'Long_MAE': [],
            'Short_MFE': [], 'Short_MAE': [],
            'Long_Hit_1R': [], 'Short_Hit_1R': []
        }
        
        # Pre-filter data for speed
        # We only care about data after 9:45
        session_data = self.df.between_time('09:45', '16:00')
        
        # Group by date for faster access
        grouped = session_data.groupby(session_data.index.date)
        
        for date, row in orb_stats.iterrows():
            current_date = date.date()
            orb_high = row['ORB_High']
            orb_low = row['ORB_Low']
            orb_range = orb_high - orb_low
            
            # Get intraday data for this date
            if current_date not in grouped.groups:
                # No data
                labels['Long_MFE'].append(0)
                labels['Long_MAE'].append(0)
                labels['Short_MFE'].append(0)
                labels['Short_MAE'].append(0)
                labels['Long_Hit_1R'].append(0)
                labels['Short_Hit_1R'].append(0)
                continue
                
            day_df = grouped.get_group(current_date)
            
            if day_df.empty:
                 labels['Long_MFE'].append(0)
                 labels['Long_MAE'].append(0)
                 labels['Short_MFE'].append(0)
                 labels['Short_MAE'].append(0)
                 labels['Long_Hit_1R'].append(0)
                 labels['Short_Hit_1R'].append(0)
                 continue

            # Convert to numpy for speed
            closes = day_df['Close'].values
            highs = day_df['High'].values
            lows = day_df['Low'].values
            
            # --- LONG Logic (Candle Close > ORB High) ---
            long_breakout_indices = np.where(closes > orb_high)[0]
            
            if len(long_breakout_indices) > 0:
                # First valid close above high
                entry_idx = long_breakout_indices[0]
                entry_price = closes[entry_idx]
                
                # Check outcome on SUBSEQUENT bars
                if entry_idx < len(closes) - 1:
                    # Look at future data
                    future_highs = highs[entry_idx+1:]
                    future_lows = lows[entry_idx+1:]
                    
                    l_mfe = np.max(future_highs) - entry_price
                    l_mae = entry_price - np.min(future_lows)
                else:
                    # Breakout on last bar? No outcome.
                    l_mfe = 0
                    l_mae = 0
            else:
                l_mfe = 0
                l_mae = 0
            
            # --- SHORT Logic (Candle Close < ORB Low) ---
            short_breakout_indices = np.where(closes < orb_low)[0]
            
            if len(short_breakout_indices) > 0:
                entry_idx = short_breakout_indices[0]
                entry_price = closes[entry_idx]
                
                if entry_idx < len(closes) - 1:
                    future_highs = highs[entry_idx+1:]
                    future_lows = lows[entry_idx+1:]
                    
                    s_mfe = entry_price - np.min(future_lows)
                    s_mae = np.max(future_highs) - entry_price
                else:
                    s_mfe = 0
                    s_mae = 0
            else:
                s_mfe = 0
                s_mae = 0
            
            labels['Long_MFE'].append(float(l_mfe))
            labels['Long_MAE'].append(float(l_mae))
            labels['Short_MFE'].append(float(s_mfe))
            labels['Short_MAE'].append(float(s_mae))
            
            labels['Long_Hit_1R'].append(1 if l_mfe >= orb_range else 0)
            labels['Short_Hit_1R'].append(1 if s_mfe >= orb_range else 0)
            
        # Attach to dataframe
        res = orb_stats.copy()
        for k, v in labels.items():
            res[k] = v
            
        return res

if __name__ == "__main__":
    from data_loader import DataLoader
    from feature_builder import FeatureBuilder
    
    # Load
    path = "ny_orb_analysis/glbx-mdp3-20100606-20191231.ohlcv-1m.csv"
    loader = DataLoader(path)
    loader.load_data()
    df = loader.preprocess()
    orb = loader.get_15m_orb_data()
    
    # Features
    fb = FeatureBuilder(df)
    fb.compute_daily_indicators()
    features = fb.build_orb_features(orb)
    
    # Labels
    lg = LabelGenerator(df)
    labeled_data = lg.generate_labels(features)
    
    print(labeled_data.head())
    labeled_data.to_csv("src/training_data.csv")
