
import pandas as pd
import numpy as np

FILE_PATH = r"C:\Users\user\Desktop\glbx-mdp3-20100606-20251003.ohlcv-1m.csv"
RTH_START = "09:30"
ORB_END = "09:45"
SESSION_END = "16:15" 

def run_backtest():
    print("Loading data...")
    # Load necessary columns
    df = pd.read_csv(FILE_PATH, usecols=['ts_event', 'open', 'high', 'low', 'close'])
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df = df.set_index('ts_event')
    
    # Timezone conversion
    if df.index.tz is None:
        df = df.tz_localize('UTC')
    df = df.tz_convert('US/Eastern')
    
    df = df.sort_index()
    df = df[~df.index.duplicated(keep='last')]
    
    print("Grouping by day...")
    grouped = df.groupby(df.index.date)
    all_days = sorted(list(grouped.groups.keys()))
    
    trades_1m = []
    trades_5m = []
    
    print(f"Processing {len(all_days)} days...")
    
    for i, day in enumerate(all_days):
        if i % 500 == 0:
            print(f"Day {i}/{len(all_days)}")
            
        day_data = grouped.get_group(day)
        
        # Define ORB Session
        orb_data = day_data.between_time(RTH_START, ORB_END)
        if orb_data.empty:
            continue
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_range = orb_high - orb_low
        
        if orb_range == 0:
            continue
            
        # Post-ORB Session for Trading
        # Start looking from the END of ORB (09:45)
        # Note: between_time is inclusive? "09:45" bar is the bar ending 09:46? 
        # OHLCV-1m usually timestamps start of bar? 
        # If 09:30 is first bar, 09:44 is 15th bar. 09:45 is start of post-ORB?
        # Let's assume standard: ORB is first 15 mins.
        # If timestamps are start-of-bar: 09:30, 31.. 44. (15 bars).
        # We start checking breakout at 09:45 bar close (which occurs at 09:46).
        
        # Slice data from 09:45 onwards
        trade_data = day_data.between_time(ORB_END, SESSION_END)
        
        if trade_data.empty:
            continue
            
        # --- Strategy 1: 1-minute Breakout ---
        # Trigger: A 1m bar CLOSE outside range
        # Start checking from the first bar of trade_data
        
        entry_price = None
        entry_time = None
        direction = 0 # 1 Long, -1 Short
        stop_price = 0
        target_price = 0
        
        # Locate first breakout candle
        # We iterate 1m bars
        for idx, row in trade_data.iterrows():
            if idx == orb_data.index[-1]: 
                continue # Skip the ORB limit bar itself if overlap
                
            close = row['close']
            
            if close > orb_high:
                # Long
                direction = 1
                entry_price = close
                entry_time = idx
                stop_price = orb_low
                target_price = entry_price + orb_range # 1:1 RR based on Entry
                # Or based on Risk (Entry - Stop)? 
                # "1:1 RR" usually means Risk = Entry - Stop. Target = Entry + Risk.
                # If Stop is fixed at ORB Low: Risk = Close - ORB Low. Target = Close + (Close - ORB Low).
                # But user said "Stop Reverse ORB". That implies Risk = Full ORB Range? 
                # "Entry Breakout... Stop Reverse ORB".
                # If breakout is huge, Risk is huge.
                # Let's use Risk = Entry - StopPrice.
                break
            elif close < orb_low:
                # Short
                direction = -1
                entry_price = close
                entry_time = idx
                stop_price = orb_high
                target_price = entry_price - (stop_price - entry_price) # 1:1
                break
        
        if entry_price:
            # Simulate Trade Outcome
            # Look at SUBSEQUENT bars
            outcome = 0 # 0 active, 1 win, -1 loss
            
            # Slice rest of day
            rest_of_day = trade_data[trade_data.index > entry_time]
            
            for _, row in rest_of_day.iterrows():
                high = row['high']
                low = row['low']
                
                if direction == 1:
                    # Check Low vs Stop first (Conservative)
                    if low <= stop_price:
                        outcome = -1
                        break
                    if high >= target_price:
                        outcome = 1
                        break
                else: # Short
                    if high >= stop_price:
                        outcome = -1
                        break
                    if low <= target_price:
                        outcome = 1
                        break
            
            # If end of day and no outcome -> Close at 16:15? 
            # Assume Loss/Scratch or Mark-to-Market. Let's count as 0 or Exit MOC.
            if outcome == 0 and not rest_of_day.empty:
                # MOC Exit
                moc_price = rest_of_day.iloc[-1]['close']
                expected_profit = target_price - entry_price
                if direction == 1:
                    pnl = moc_price - entry_price
                else:
                    pnl = entry_price - moc_price
                
                # Normalize outcome for stats (Float win?)
                outcome = pnl / abs(entry_price - stop_price) # R-multiple
            elif outcome != 0:
                # Fixed 1R or -1R
                # Wait, if gap past stop? We assume fill at Stop for sim simplicity unless gap is tracked.
                # 1m data gaps are small usually.
                pass
                
            trades_1m.append({
                'date': day,
                'type': '1m_breakout',
                'dir': direction,
                'entry': entry_price,
                'stop': stop_price,
                'target': target_price,
                'outcome': outcome, # 1, -1, or R-multiple
                'orb_range': orb_range
            })

        # --- Strategy 2: 5-minute Breakout ---
        # Resample post-ORB data to 5m
        # 09:45, 09:50, 09:55...
        # label='right' so 09:45-09:50 bar is labeled 09:50? 
        # Standard: 09:45 bar closes at 09:50.
        
        # We need to include the 09:45 start point correctly.
        # trade_data starts > 09:45? 
        # Let's resample the WHOLE day then slice? Better accuracy.
        
        day_5m = day_data.resample('5T', label='right', closed='right').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
        # Filter for time > 09:45
        # ORB logic: 09:45 is the end of ORB.
        # The first candidate bar is the 09:45-09:50 bar (labeled 09:50).
        
        trade_data_5m = day_5m.between_time("09:46", SESSION_END) # start 09:46 to catch 09:50 bar?
        
        entry_price_5 = None
        entry_time_5 = None
        direction_5 = 0
        stop_price_5 = 0
        target_price_5 = 0
        
        for idx, row in trade_data_5m.iterrows():
            close = row['close']
             
            if close > orb_high:
                direction_5 = 1
                entry_price_5 = close
                entry_time_5 = idx
                stop_price_5 = orb_low
                target_price_5 = entry_price_5 + (entry_price_5 - stop_price_5)
                break
            elif close < orb_low:
                direction_5 = -1
                entry_price_5 = close
                entry_time_5 = idx
                stop_price_5 = orb_high
                target_price_5 = entry_price_5 - (stop_price_5 - entry_price_5) 
                break
                
        if entry_price_5:
            # Simulate Outcome using 1m data for precision!
            # We entered at 5m Close key (e.g. 09:50). 
            # Check price action from 09:50 onwards in 1m data.
            
            outcome_5 = 0
            rest_of_day_1m = day_data[day_data.index > entry_time_5] # strict >
            
            for _, row in rest_of_day_1m.iterrows():
                high = row['high']
                low = row['low']
                
                if direction_5 == 1:
                    if low <= stop_price_5:
                        outcome_5 = -1
                        break
                    if high >= target_price_5:
                        outcome_5 = 1
                        break
                else:
                    if high >= stop_price_5:
                        outcome_5 = -1
                        break
                    if low <= target_price_5:
                        outcome_5 = 1
                        break
            
            if outcome_5 == 0 and not rest_of_day_1m.empty:
               moc_price = rest_of_day_1m.iloc[-1]['close']
               if direction_5 == 1:
                   outcome_5 = (moc_price - entry_price_5) / (entry_price_5 - stop_price_5)
               else:
                   outcome_5 = (entry_price_5 - moc_price) / (stop_price_5 - entry_price_5)
                   
            trades_5m.append({
                'date': day,
                'type': '5m_breakout',
                'dir': direction_5,
                'entry': entry_price_5,
                'stop': stop_price_5,
                'target': target_price_5,
                'outcome': outcome_5,
                'orb_range': orb_range
            })

    # Save results
    df_1m = pd.DataFrame(trades_1m)
    df_5m = pd.DataFrame(trades_5m)
    
    df_1m.to_csv("trades_1m.csv", index=False)
    df_5m.to_csv("trades_5m.csv", index=False)
    
    print("\nResults Summary:")
    print("-" * 30)
    for name, df_res in [("1-min Breakout", df_1m), ("5-min Breakout", df_5m)]:
        if df_res.empty:
            print(f"{name}: No trades.")
            continue
            
        # Win Rate (Full Wins)
        wins = len(df_res[df_res['outcome'] >= 1])
        losses = len(df_res[df_res['outcome'] <= -1])
        total = len(df_res)
        
        win_rate = wins / total
        avg_r = df_res['outcome'].mean()
        
        print(f"{name}:")
        print(f"  Trades: {total}")
        print(f"  Win Rate (1R hit): {win_rate:.2%}")
        print(f"  Avg Return (R): {avg_r:.3f}R")
        
        # Cumulative R
        print(f"  Total Return: {df_res['outcome'].sum():.2f}R")

if __name__ == "__main__":
    run_backtest()
